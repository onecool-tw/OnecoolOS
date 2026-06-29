# Contributing

This document describes the Onecool OS development workflow.

## Development Principles

- Do not redesign the architecture unless explicitly instructed.
- Follow the existing repository structure.
- Keep every milestone executable.
- Include tests for every milestone.
- Update README when behavior changes.
- Keep modules loosely coupled.
- Prefer composition over inheritance.
- Keep business logic inside modules.
- Keep infrastructure independent of business modules.
- Follow PEP8 and Python best practices.
- Do not leave TODO placeholders for completed milestones.
- Fix discovered defects before marking a milestone complete.

## Setup

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Run tests:

```bash
python -m pytest
```

Run the CLI:

```bash
python -m onecool_os status
```

## Workflow

1. Start from the latest `main`.
2. Make a focused change for the current milestone.
3. Add or update tests.
4. Update README and docs if behavior changes.
5. Run the full test suite.
6. Commit using Conventional Commits.
7. Push to GitHub.

## Commit Messages

Use Conventional Commits:

```text
type(scope): summary
```

Examples:

```text
docs: initialize project documentation
feat(core): add plugin lifecycle
fix(core): prevent duplicate service registration
test(core): cover engine restart
```

## Pull Request Expectations

Every change should include:

- A concise summary.
- Tests for changed behavior.
- Documentation updates when behavior changes.
- Confirmation that tests pass.

## Module Development

Future modules such as Market, Funds, Cards, House, Emergency, and Dashboard
should be added without changing Core Engine responsibilities. Prefer plugin
entry points and explicit service registration over direct coupling.
