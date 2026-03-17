#!/usr/bin/env python3

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any


DOTFILES_TO_TRACK = [
    ".zshrc",
    ".zprofile",
    ".zshenv",
    ".zlogin",
    ".bash_profile",
    ".bashrc",
    ".profile",
    ".gitconfig",
    ".gitignore_global",
    ".p10k.zsh",
    ".tool-versions",
    ".npmrc",
    ".config/starship.toml",
    ".ssh/config",
]


BOOTSTRAP_TOOL_MARKERS = {
    "oh-my-zsh": [".oh-my-zsh"],
    "nvm": [".nvm"],
    "pyenv": [".pyenv"],
    "rbenv": [".rbenv"],
    "asdf": [".asdf"],
    "sdkman": [".sdkman"],
    "rustup": [".rustup", ".cargo/bin/rustup"],
    "volta": [".volta"],
    "fnm": [".fnm"],
    "bun": [".bun"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Inventory a macOS workstation and write a rebuild-friendly report "
            "covering packages, apps, shell setup, and selected tool configs."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory to write the inventory into. Defaults to ./mac-inventory-<timestamp>.",
    )
    parser.add_argument(
        "--copy-dotfiles",
        action="store_true",
        help="Copy selected dotfiles into the output directory for backup/reference.",
    )
    parser.add_argument(
        "--skip-pkgutil",
        action="store_true",
        help="Skip installed package receipts export if you do not need it.",
    )
    return parser.parse_args()


def now_utc() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat()


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def run_command(command: list[str], timeout: int = 120) -> dict[str, Any]:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return {
            "ok": False,
            "exit_code": None,
            "stdout": "",
            "stderr": f"Command not found: {command[0]}",
        }
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "exit_code": None,
            "stdout": "",
            "stderr": f"Timed out after {timeout}s: {' '.join(command)}",
        }

    return {
        "ok": result.returncode == 0,
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def collect_system() -> dict[str, Any]:
    sw_vers = run_command(["sw_vers"])
    uname = run_command(["uname", "-a"])
    uptime = run_command(["uptime"])
    disk = run_command(["df", "-h", "/"])

    return {
        "captured_at_utc": now_utc(),
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python": sys.version,
        "sw_vers": sw_vers["stdout"].strip(),
        "uname": uname["stdout"].strip(),
        "uptime": uptime["stdout"].strip(),
        "root_disk": disk["stdout"].strip(),
    }


def collect_shell() -> dict[str, Any]:
    home = Path.home()
    dotfiles: list[dict[str, Any]] = []
    for relative_path in DOTFILES_TO_TRACK:
        full_path = home / relative_path
        if full_path.exists():
            stat = full_path.stat()
            dotfiles.append(
                {
                    "path": str(full_path),
                    "size_bytes": stat.st_size,
                    "modified": dt.datetime.fromtimestamp(stat.st_mtime, dt.UTC)
                    .replace(microsecond=0)
                    .isoformat(),
                }
            )

    custom_plugins_dir = home / ".oh-my-zsh/custom/plugins"
    custom_plugins = sorted(
        [entry.name for entry in custom_plugins_dir.iterdir() if entry.is_dir()]
    ) if custom_plugins_dir.exists() else []

    return {
        "shell": os.environ.get("SHELL", ""),
        "oh_my_zsh_installed": (home / ".oh-my-zsh").exists(),
        "oh_my_zsh_custom_plugins": custom_plugins,
        "tracked_dotfiles": dotfiles,
    }


def collect_bootstrap_tools() -> dict[str, Any]:
    home = Path.home()
    detected: list[dict[str, str]] = []

    for tool_name, markers in BOOTSTRAP_TOOL_MARKERS.items():
        for marker in markers:
            candidate = home / marker
            if candidate.exists():
                detected.append({"tool": tool_name, "evidence": str(candidate)})
                break

    return {"detected": detected}


def collect_applications() -> dict[str, Any]:
    app_roots = [Path("/Applications"), Path.home() / "Applications"]
    apps: list[dict[str, str]] = []

    for root in app_roots:
        if not root.exists():
            continue
        for app in sorted(root.glob("*.app")):
            apps.append({"name": app.name, "path": str(app)})

    return {"applications": apps}


def collect_brew(output_dir: Path) -> dict[str, Any]:
    if not command_exists("brew"):
        return {"installed": False}

    brew_info = {
        "installed": True,
        "brew_path": shutil.which("brew"),
        "brew_version": run_command(["brew", "--version"])["stdout"].strip(),
        "formulae": run_command(["brew", "list", "--formula"])["stdout"].splitlines(),
        "casks": run_command(["brew", "list", "--cask"])["stdout"].splitlines(),
        "leaves": run_command(["brew", "leaves"])["stdout"].splitlines(),
        "services": run_command(["brew", "services", "list"])["stdout"].strip(),
    }

    brewfile_path = output_dir / "Brewfile"
    dump = run_command(
        [
            "brew",
            "bundle",
            "dump",
            "--force",
            "--describe",
            f"--file={brewfile_path}",
        ],
        timeout=180,
    )
    brew_info["brewfile_written"] = dump["ok"] and brewfile_path.exists()
    if not dump["ok"]:
        brew_info["brewfile_error"] = dump["stderr"].strip() or dump["stdout"].strip()

    return brew_info


def collect_app_store() -> dict[str, Any]:
    if not command_exists("mas"):
        return {
            "installed": False,
            "note": "Install mas to export Mac App Store purchases with `mas list`.",
        }

    listing = run_command(["mas", "list"], timeout=180)
    return {
        "installed": True,
        "apps": listing["stdout"].splitlines(),
        "error": listing["stderr"].strip(),
    }


def collect_npm() -> dict[str, Any]:
    if not command_exists("npm"):
        return {"installed": False}

    result = run_command(["npm", "list", "-g", "--depth=0", "--json"], timeout=180)
    payload: dict[str, Any] = {"installed": True}
    if result["ok"] and result["stdout"].strip():
        try:
            payload["packages"] = json.loads(result["stdout"])
        except json.JSONDecodeError:
            payload["raw"] = result["stdout"]
    else:
        payload["error"] = result["stderr"].strip() or result["stdout"].strip()
    return payload


def collect_pipx() -> dict[str, Any]:
    if not command_exists("pipx"):
        return {
            "installed": False,
            "note": "Install pipx if you use Python CLIs and want them inventoried cleanly.",
        }

    result = run_command(["pipx", "list", "--json"], timeout=180)
    payload: dict[str, Any] = {"installed": True}
    if result["ok"] and result["stdout"].strip():
        try:
            payload["packages"] = json.loads(result["stdout"])
        except json.JSONDecodeError:
            payload["raw"] = result["stdout"]
    else:
        payload["error"] = result["stderr"].strip() or result["stdout"].strip()
    return payload


def collect_cargo() -> dict[str, Any]:
    if not command_exists("cargo"):
        return {"installed": False}

    result = run_command(["cargo", "install", "--list"], timeout=180)
    return {
        "installed": True,
        "packages": result["stdout"].splitlines(),
        "error": result["stderr"].strip(),
    }


def collect_gems() -> dict[str, Any]:
    if not command_exists("gem"):
        return {"installed": False}

    result = run_command(["gem", "list"], timeout=180)
    return {
        "installed": True,
        "packages": result["stdout"].splitlines(),
        "error": result["stderr"].strip(),
    }


def collect_pkgutil(skip_pkgutil: bool) -> dict[str, Any]:
    if skip_pkgutil:
        return {"skipped": True}

    result = run_command(["pkgutil", "--pkgs"], timeout=300)
    return {
        "skipped": False,
        "packages": result["stdout"].splitlines(),
        "error": result["stderr"].strip(),
    }


def collect_login_items() -> dict[str, Any]:
    result = run_command(
        [
            "osascript",
            "-e",
            'tell application "System Events" to get the name of every login item',
        ],
        timeout=120,
    )
    output = result["stdout"].strip()
    items = [item.strip() for item in output.split(",") if item.strip()] if output else []
    return {
        "items": items,
        "error": result["stderr"].strip(),
    }


def copy_dotfiles(output_dir: Path, shell_info: dict[str, Any]) -> list[str]:
    copied: list[str] = []
    backup_root = output_dir / "dotfiles"
    for entry in shell_info.get("tracked_dotfiles", []):
        source = Path(entry["path"])
        destination = backup_root / source.relative_to(Path.home())
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied.append(str(destination))
    return copied


def build_recommendations(inventory: dict[str, Any]) -> list[str]:
    recommendations: list[str] = []
    if inventory["app_store"].get("installed") is False:
        recommendations.append("Install `mas` before the next run if you want App Store purchases included.")
    if inventory["pipx"].get("installed") is False:
        recommendations.append("If you rely on Python CLIs, decide whether you want them standardized through `pipx`.")
    if inventory["brew"].get("installed"):
        recommendations.append("Use the generated Brewfile as the base of your rebuild automation and prune anything you do not want on the new Mac.")
    if inventory["bootstrap_tools"].get("detected"):
        recommendations.append("Review the bootstrap-tools export for curl or installer-based shell tooling that may not show up in Homebrew or App Store inventories.")
    recommendations.append("Review the applications and pkgutil exports for manually installed vendor software that Homebrew and App Store do not cover.")
    recommendations.append("Move durable shell, git, and SSH config into a dotfiles repo or chezmoi so the next rebuild is mostly declarative.")
    return recommendations


def write_summary(output_dir: Path, inventory: dict[str, Any]) -> None:
    apps_count = len(inventory["applications"]["applications"])
    brew_formulae = len(inventory["brew"].get("formulae", []))
    brew_casks = len(inventory["brew"].get("casks", []))
    dotfiles = len(inventory["shell"]["tracked_dotfiles"])
    app_store_count = len(inventory["app_store"].get("apps", []))
    login_items_count = len(inventory["login_items"].get("items", []))
    bootstrap_tools = inventory["bootstrap_tools"].get("detected", [])
    bootstrap_names = ", ".join(item["tool"] for item in bootstrap_tools) or "none"

    lines = [
        "# Mac Inventory Summary",
        "",
        f"Captured: {inventory['system']['captured_at_utc']}",
        f"Host: {inventory['system']['hostname']}",
        f"Platform: {inventory['system']['platform']}",
        "",
        "## Counts",
        f"- Applications found: {apps_count}",
        f"- Homebrew formulae: {brew_formulae}",
        f"- Homebrew casks: {brew_casks}",
        f"- Tracked dotfiles present: {dotfiles}",
        f"- Bootstrap tools detected: {len(bootstrap_tools)}",
        f"- App Store apps exported: {app_store_count}",
        f"- Login items found: {login_items_count}",
        "",
        "## Shell And Bootstrap",
        f"- Oh My Zsh installed: {inventory['shell']['oh_my_zsh_installed']}",
        f"- Oh My Zsh custom plugins: {', '.join(inventory['shell']['oh_my_zsh_custom_plugins']) or 'none'}",
        f"- Bootstrap tool markers: {bootstrap_names}",
        "",
        "## Follow-up",
    ]
    lines.extend(f"- {item}" for item in inventory["recommendations"])
    lines.extend(
        [
            "",
            "## Files",
            "- inventory.json: full machine-readable export",
            "- Brewfile: Homebrew reinstall base, if brew was available",
            "- applications.txt: top-level .app bundles in /Applications and ~/Applications",
            "- bootstrap-tools.txt: home-directory tools commonly installed via curl/bootstrap scripts",
            "- pkgutil-packages.txt: installer receipts for manually installed packages",
            "",
        ]
    )
    write_text(output_dir / "SUMMARY.md", "\n".join(lines))


def write_supporting_files(output_dir: Path, inventory: dict[str, Any]) -> None:
    applications = [entry["path"] for entry in inventory["applications"]["applications"]]
    write_text(output_dir / "applications.txt", "\n".join(applications) + "\n")

    write_text(
        output_dir / "app-store.txt",
        "\n".join(inventory["app_store"].get("apps", [])) + "\n",
    )
    write_text(
        output_dir / "bootstrap-tools.txt",
        "\n".join(
            f"{entry['tool']}\t{entry['evidence']}"
            for entry in inventory["bootstrap_tools"].get("detected", [])
        )
        + "\n",
    )
    write_text(
        output_dir / "pkgutil-packages.txt",
        "\n".join(inventory["pkgutil"].get("packages", [])) + "\n",
    )
    write_text(
        output_dir / "login-items.txt",
        "\n".join(inventory["login_items"].get("items", [])) + "\n",
    )


def main() -> int:
    args = parse_args()
    timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    output_dir = args.output_dir or (Path.cwd() / f"mac-inventory-{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)

    inventory: dict[str, Any] = {
        "system": collect_system(),
        "shell": collect_shell(),
        "bootstrap_tools": collect_bootstrap_tools(),
        "applications": collect_applications(),
        "brew": collect_brew(output_dir),
        "app_store": collect_app_store(),
        "npm": collect_npm(),
        "pipx": collect_pipx(),
        "cargo": collect_cargo(),
        "gems": collect_gems(),
        "pkgutil": collect_pkgutil(args.skip_pkgutil),
        "login_items": collect_login_items(),
    }

    if args.copy_dotfiles:
        inventory["dotfiles_backup"] = {"copied_files": copy_dotfiles(output_dir, inventory["shell"])}
    else:
        inventory["dotfiles_backup"] = {"copied_files": []}

    inventory["recommendations"] = build_recommendations(inventory)

    write_json(output_dir / "inventory.json", inventory)
    write_supporting_files(output_dir, inventory)
    write_summary(output_dir, inventory)

    print(f"Inventory written to {output_dir}")
    print(f"Summary: {output_dir / 'SUMMARY.md'}")
    print(f"JSON: {output_dir / 'inventory.json'}")
    if inventory["brew"].get("brewfile_written"):
        print(f"Brewfile: {output_dir / 'Brewfile'}")
    if args.copy_dotfiles:
        print(f"Dotfiles backup: {output_dir / 'dotfiles'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())