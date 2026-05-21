"""
invoke tasks — local developer workflow for building and publishing pyghidra_decaf.

Publishing to the PyPI Package Registry requires a ~/.pypirc file
with a [pyghidra_decaf] section.  See PUBLISHING.md for the full setup guide.

Quick reference:
  inv install-tools   install build and twine into the current environment
  inv build           clean then build wheel + sdist into pyghidra_decaf/dist/
  inv publish         upload pyghidra_decaf/dist/* to the registry via twine
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
    """Upload pyghidra_decaf/dist/* to the package registry via twine.

    Reads the repository URL and credentials from ~/.pypirc under the
    [pyghidra_decaf] section.  Run `inv build` first if dist/ is empty.
    """
    ctx.run("python -m twine upload --repository pyghidra_decaf pyghidra_decaf/dist/*")
