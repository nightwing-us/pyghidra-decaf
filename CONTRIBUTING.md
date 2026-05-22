# Contributing to pyghidra-decaf

Thank you for your interest in contributing to `pyghidra-decaf`.  Contributions
of all kinds are welcome: bug reports, documentation improvements, and code
patches.

---

## Code of Conduct

All interactions in this project are governed by our
[Code of Conduct](CODE_OF_CONDUCT.md).  Please read it before participating.

---

## Development Setup

### Prerequisites

- Python 3.10 or later
- A working [Ghidra](https://ghidra-sre.org/) installation (required at runtime;
  not needed for lint/typecheck-only work)

### Clone and install

```bash
git clone https://github.com/nightwing-us/pyghidra-decaf.git
cd pyghidra-decaf/pyghidra_decaf
pip install -e ".[dev]"
```

### Running the test suite

```bash
cd pyghidra_decaf
pytest --tb=short
```

### Linting

```bash
ruff check src tests
```

### Type-checking

```bash
mypy
```

All three commands must pass before submitting a pull request.  The CI workflow
runs them automatically on every PR.

---

## DCO Sign-Off Requirement

This project uses the **Developer Certificate of Origin (DCO)** to confirm that
contributors have the right to submit their contributions under the project
license.

Every commit in your pull request must carry a `Signed-off-by:` trailer:

```
Signed-off-by: Jane Doe <jane@example.com>
```

The name and email must match your real identity.  Add it automatically with
the `-s` flag:

```bash
git commit -s -m "fix: correct handling of null DECAF response"
```

By signing off you certify that you agree to the terms at
<https://developercertificate.org/>.  The full DCO text is reproduced there;
the core statement is: you wrote the code (or have the right to submit it),
and you grant the project the right to use it under the Apache-2.0 license.

**DCO enforcement:** A status check on every pull request verifies that all
commits are signed off.  Pull requests without signed-off commits cannot be
merged.

---

## Pull Request Process

### Branch naming

Use a short, descriptive branch name prefixed with the change type:

```
fix/bootstrap-subprocess-leak
feat/stream-decaf-output
docs/update-plugin-example
chore/bump-ruff-version
```

### Commit messages

This repository uses [Conventional Commits](https://www.conventionalcommits.org/).
Please format commit messages as:

```
<type>(<optional scope>): <short description>

<optional body>

Signed-off-by: Jane Doe <jane@example.com>
```

Common types: `fix`, `feat`, `docs`, `chore`, `ci`, `refactor`, `test`.

### Before pushing

Run the full local check suite:

```bash
ruff check src tests
mypy
pytest --tb=short
```

### Opening the PR

- Target the `main` branch.
- Fill in the PR description with what changed and why.
- Link any related issues.
- Ensure all CI checks pass.

### How your contribution lands

This repository is a **public mirror** of an internal source of truth.
Maintainers review and approve pull requests on GitHub, then **cherry-pick**
approved commits into the internal repository:

```bash
# Maintainer runs internally:
git cherry-pick -x <PR-commit-hash>
```

Because of this workflow, your PR will be **closed** (not merged via the GitHub
"Merge" button) once the cherry-pick is accepted.  The maintainer will post a
comment such as:

> Landed in v1.2.3 — commit abc1234.  Thanks!

Your change will appear in the public mirror at the next release.  This is
intentional and does not mean your contribution was rejected.

---

## Code Style

- **Formatter:** [ruff](https://docs.astral.sh/ruff/) with the configuration in
  `pyghidra_decaf/pyproject.toml` (`[tool.ruff]`).
- **Type-checking:** [mypy](https://mypy.readthedocs.io/) in strict mode.  All
  public functions and methods must have complete type annotations.  Do not use
  `Any`; if you genuinely need it, add an inline comment explaining why and
  expect discussion in review.
- **Import ordering:** [isort](https://pycqa.github.io/isort/) with
  `profile = "pycharm"` (configured in `pyproject.toml`).
- **Line length:** 120 characters (prose in docstrings: 80 characters).
- **String quotes:** single quotes preferred (ruff enforces this).

When in doubt, run `ruff check --fix` and `ruff format` to auto-correct most
style issues before committing.

---

## Reporting Bugs

Open an issue on [GitHub Issues](https://github.com/nightwing-us/pyghidra-decaf/issues).

For security vulnerabilities, see [SECURITY.md](SECURITY.md).

---

## Questions

Feel free to open a GitHub Discussion or comment on a relevant issue.
