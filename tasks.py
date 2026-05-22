"""
invoke tasks — local developer workflow for building pyghidra_decaf.

Releases to PyPI are published from GitHub Actions via the OIDC trusted-
publisher flow in .github/workflows/release.yml on every v* tag push; this
file only covers the local build and (optionally) a manual twine upload.

Quick reference:
  inv install-tools   install build and twine into the current environment
  inv build           clean then build wheel + sdist into pyghidra_decaf/dist/
  inv publish         upload pyghidra_decaf/dist/* to PyPI via twine
  inv clean           remove pyghidra_decaf/dist/, build artifacts, and egg-info
"""

from invoke import task


@task
def install_tools(ctx):
    """Install build and twine into the current Python environment."""
    ctx.run("pip install --upgrade build twine")


@task
def clean(ctx):
    """Remove dist/, build artifacts, egg-info directories, and compiled bytecode."""
    ctx.run("rm -rf pyghidra_decaf/dist/")
    ctx.run("rm -rf pyghidra_decaf/build/")
    ctx.run("rm -rf pyghidra_decaf/src/*.egg-info")
    ctx.run("rm -rf pyghidra_decaf/src/pyghidra_decaf.egg-info")
    ctx.run("find . -type d -name __pycache__ -not -path './.git/*' -exec rm -rf {} +")
    ctx.run("find . -name '*.pyc' -not -path './.git/*' -delete")


@task(pre=[clean])
def build(ctx):
    """Clean then build the wheel and sdist into pyghidra_decaf/dist/ using python -m build."""
    with ctx.cd("pyghidra_decaf"):
        ctx.run("python -m build")


@task
def publish(ctx):
    """Manually upload pyghidra_decaf/dist/* to PyPI via twine.

    Normal releases are published automatically by .github/workflows/release.yml
    when a v* tag is pushed; use this task only for one-off local uploads.
    Reads credentials from ~/.pypirc (or TWINE_USERNAME / TWINE_PASSWORD).
    Run `inv build` first if dist/ is empty.
    """
    ctx.run("python -m twine upload pyghidra_decaf/dist/*")
