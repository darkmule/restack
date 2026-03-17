# restack PRD

## Summary

`restack` is a macOS workstation migration tool. It captures the software, shell tooling, and environment setup that define a working Mac, then turns that information into a practical, reviewable path for standing up a new Mac with minimal guesswork.

## Problem

When moving to a new Mac, the hardest part is not copying files. It is reconstructing the working environment:

- package-managed tools
- apps installed from multiple sources
- shell bootstrap tools
- language-specific CLIs
- selected user configuration
- vendor and corporate software that is installed outside normal package managers

Most of that setup lives in fragments across Homebrew, App Store, shell dotfiles, hidden directories, `.pkg` installers, and ad hoc manual steps. As a result, users often discover missing pieces only after they start working on the new machine.

## Users

Primary user:

- an individual developer or power user migrating from one Mac to another

Possible later users:

- consultants who repeatedly set up Mac workstations
- small teams wanting a light-weight standard rebuild process

## Goals

- Make the current Mac setup visible in one place.
- Export a rebuild-friendly representation of that setup.
- Distinguish what can be automated from what remains manual.
- Reduce omission risk during Mac migration.
- Provide a reviewable, non-magic path to rebuilding a machine.

## Non-Goals

- full file backup and restore
- replacing MDM, Jamf, or corporate enrollment workflows
- deep system preference cloning in the first version
- perfect detection of every installed artifact on macOS
- unattended zero-review machine provisioning in the first version

## Product Principles

- Explicit over magical: users should be able to see exactly what was detected and how it will be reapplied.
- Review before mutation: applying changes to a new Mac should be deliberate, not opaque.
- Separate reproducible from manual: the tool should not pretend everything is automatable.
- Practical over exhaustive: cover the major setup categories first, not every edge case.
- Keep scope distinct from backup tools: workstation rebuild is a different problem than file preservation.

## Current State

Current implementation:

- [restack.py](/Users/mark.duell/workspace/restack/restack.py)

Current capabilities:

- system inventory
- applications scan
- Homebrew export and Brewfile generation
- shell/dotfile metadata collection
- detection of bootstrap-installed tools like Oh My Zsh and pyenv
- npm, pipx, cargo, gem introspection where available
- login item capture
- `pkgutil` receipt export

Current outputs:

- `inventory.json`
- `SUMMARY.md`
- `Brewfile`
- `applications.txt`
- `bootstrap-tools.txt`
- `app-store.txt`
- `login-items.txt`
- `pkgutil-packages.txt`

## Proposed Workflow

### 1. Scan

Purpose:

- inspect the current Mac and emit a structured inventory

Likely command:

- `restack scan`

Key outputs:

- normalized inventory artifact
- human-readable summary
- source-specific exports such as Brewfile

### 2. Plan

Purpose:

- convert raw inventory into a rebuild plan grouped by install source and confidence level

Likely command:

- `restack plan`

Expected behavior:

- categorize tools and apps by source
- mark items as automated, semi-automated, or manual
- generate a checklist for unresolved/manual steps

### 3. Apply

Purpose:

- execute the safe, reproducible parts of the rebuild on the new Mac

Likely command:

- `restack apply`

Expected behavior:

- install Homebrew prerequisites
- apply Brewfile or equivalent package plan
- optionally restore selected dotfiles or bootstrap tools
- stop short of corporate-managed or risky flows unless explicitly instructed

### 4. Doctor

Purpose:

- validate whether the rebuilt machine matches the plan closely enough

Likely command:

- `restack doctor`

Expected behavior:

- compare expected versus actual state
- highlight missing items and likely causes
- recommend next manual actions

## Key Concepts

### Inventory

A point-in-time scan of the current Mac.

### Plan

A classified rebuild artifact that says:

- what should be installed
- from which source
- how confidently it can be automated
- what remains manual

### Apply Surface

The subset of the plan that `restack` is allowed to enact automatically.

### Manual Surface

Items that require review, login, enterprise enrollment, licensing, or vendor-specific installers.

## Decisions Already Made

- Name: `restack`
- Product scope includes both inventory and rebuild assistance
- Tool remains separate from the existing backup utility `stash`
- Current script should be treated as the seed implementation, not the final architecture
- VS Code extensions are out of scope for now because built-in sync already handles that use case

## Open Questions

- Should App Store integration be first-class, or treated as optional behind `mas`?
- Should dotfiles be copied, referenced, or delegated to a tool like `chezmoi`?
- Should `apply` ever run curl/bootstrap installers directly, or only emit instructions for them?
- How should corporate-managed apps be detected and classified?
- Should package-manager-specific collectors stay separate or normalize into one schema immediately?
- What is the right boundary between helpful automation and risky mutation?
- Should the first proper implementation remain a single script, or move to a small packaged CLI early?

## Risks

- Overpromising reproducibility when some workstation state is inherently manual or enterprise-controlled
- Expanding into backup or general workstation management and losing product clarity
- Treating raw `pkgutil` data as more authoritative than it really is
- Building too much command surface before the data model is stable

## Near-Term Milestones

### Milestone 1: Improve Scan Fidelity

- classify detected items by likely install source
- improve shell/bootstrap detection
- separate signal from noisy `pkgutil` output

### Milestone 2: Introduce Plan Artifact

- define a plan schema
- map inventory items to rebuild actions
- mark manual versus automatable items explicitly

### Milestone 3: Add Conservative Apply

- support safe package-manager-driven installs first
- avoid corporate/vendor flows unless intentionally invoked

### Milestone 4: Add Validation

- compare a machine against a plan and report drift or omissions

## Handoff Notes For Future Agents

- Start from [restack.py](/Users/mark.duell/workspace/restack/restack.py) as the working implementation.
- Preserve the product boundary: `restack` is about Mac setup reconstruction, not file backup.
- Keep the user-facing model simple: scan, plan, apply, doctor.
- Prefer explicit outputs and reviewable artifacts over hidden automation.