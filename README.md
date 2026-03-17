# restack

`restack` inventories the apps, packages, shell tools, and configuration that define a Mac setup, then helps rebuild that setup on a new Mac with less guesswork and less manual effort.

## Why

Moving to a new Mac is rarely just a matter of reinstalling a few apps. The real working setup usually spans:

- Homebrew formulae and casks
- App Store apps
- shell tooling installed via curl or bootstrap scripts
- language-specific CLIs
- dotfiles and environment configuration
- login items and vendor-managed software
- corporate or security tools that are easy to forget until they are missing

`restack` exists to make that setup visible, exportable, and progressively reproducible.

## Current Status

This repository is at an early stage. The current implementation is a standalone Python script:

- [restack.py](/Users/mark.duell/workspace/restack/restack.py)

Today it focuses on inventory generation. It can currently scan a Mac and export:

- system information
- installed application bundles
- Homebrew formulae, casks, leaves, and Brewfile
- selected shell and dotfile metadata
- bootstrap-installed tooling such as Oh My Zsh and pyenv
- npm, gem, cargo, and pipx availability/details where applicable
- login items
- installer receipts via `pkgutil`

The script writes a machine-readable JSON export plus supporting text files and a human-readable summary.

## Current Usage

Run the script directly:

```bash
python3 restack.py
```

Or specify an output location:

```bash
python3 restack.py --output-dir ~/restack-output
```

Optional flags:

- `--copy-dotfiles` to back up selected dotfiles into the output directory
- `--skip-pkgutil` to skip installer receipt export

## Intended Direction

`restack` is intended to grow from a one-off inventory script into a small workstation migration tool with a clear lifecycle:

1. Scan the current Mac
2. Produce a rebuild plan
3. Apply the reproducible parts on a new Mac
4. Highlight the manual or corporate-managed steps that still require attention

The likely command model is:

- `restack scan`
- `restack plan`
- `restack apply`
- `restack doctor`

Those commands are directional only at this stage. They are not implemented yet.

## Product Boundary

`restack` is intentionally separate from file backup tools.

- `restack` is about workstation composition and rebuild
- backup tools are about preserving and restoring file content

That distinction matters because software inventory and setup automation have different data models, risks, and recovery paths than file backup.

## Documentation

Product direction, scope, assumptions, and open questions are tracked in:

- [docs/PRD.md](/Users/mark.duell/workspace/restack/docs/PRD.md)

## Near-Term Goals

- tighten the inventory model so outputs are categorized by install source
- distinguish reproducible installs from manual/vendor-managed installs
- define the shape of the rebuild plan artifact
- decide how aggressive `apply` should be versus how much should remain manual

## Non-Goals For Now

- full file backup and restore
- replacing MDM or corporate onboarding flows
- silently auto-installing everything without review
- supporting non-macOS platforms in the initial version

## A Poem

*Ode to the New Machine*

A blank Mac waits, all polished, clean,
No trace of tools that once had been.
The terminal sits silent, bare —
Where did my aliases go from there?

I scan, I list, I capture all:
Each brew, each gem, each cask installed,
Each dotfile tucked in hidden space,
Each login item finding place.

Then comes the day of the new machine,
The restack plan, the rebuild dream:
Apply the known, flag what remains,
And boot your workflow, whole again.
