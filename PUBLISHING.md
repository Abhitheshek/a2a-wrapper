# Publishing Guide

## Free places to host this project

For a public Python wrapper, the practical free setup is:

- source code on GitHub
- installable package on PyPI
- optional test releases on TestPyPI

This gives you:

- free code hosting
- free issue tracking and README/docs hosting
- normal `pip install ...` support for users

## Recommended package name

Current distribution name:

- `a2a-wrapper`

Current import name:

- `a2a_wrapper`

Important:

- the package is installed with `pip install a2a-wrapper`
- the code is imported with `import a2a_wrapper`

## Before publishing

Make sure these are done:

1. Replace the placeholder URLs in `pyproject.toml`:
   - `Homepage`
   - `Documentation`
   - `Repository`
2. Push the repository to GitHub.
3. Make sure your default branch is correct.
4. Run tests locally:

```bash
pytest
```

5. Build locally:

```bash
python -m build --no-isolation
```

## Local build

```bash
python -m pip install --upgrade pip build
python -m build
```

## Local install test

```bash
pip install dist/*.whl
```

Then test:

```python
from a2a_wrapper import AgentClient, AgentServerConfig, AgentCapability, create_agent_server
```

## Publish to TestPyPI first

```bash
python -m pip install --upgrade twine
twine upload --repository testpypi dist/*
```

Then test install from TestPyPI:

```bash
pip install --index-url https://test.pypi.org/simple/ a2a-wrapper
```

## Publish to PyPI using GitHub Actions

This repo already includes:

- `.github/workflows/ci.yml`
- `.github/workflows/publish.yml`

Recommended flow:

1. Push this repository to GitHub.
2. Create a PyPI account if you do not already have one.
3. Create a PyPI project named `a2a-wrapper` if the name is available.
4. In PyPI, configure GitHub Actions as a Trusted Publisher for `.github/workflows/publish.yml`.
5. Grant the publisher access to your real GitHub repository.
6. Commit your final package version.
7. Push a version tag like `v0.2.0`.
8. GitHub Actions will build and publish the package automatically.

## Trusted Publisher setup

In PyPI:

1. Open your PyPI project settings.
2. Go to Publishing.
3. Add a Trusted Publisher.
4. Select GitHub.
5. Fill:
   - repository owner
   - repository name
   - workflow file: `publish.yml`
   - environment name: `pypi`
6. Save it.

Then in GitHub:

1. Make sure `.github/workflows/publish.yml` exists in the default branch.
2. If you use GitHub environments, create an environment named `pypi`.
3. Push a tag like:

```bash
git tag v0.2.0
git push origin v0.2.0
```

## User install command

After publishing, users can install it with:

```bash
pip install a2a-wrapper
```

And use it with:

```python
from a2a_wrapper import AgentClient, AgentServer, AgentServerConfig, AgentCapability
```

## Helpful official references

- Python Packaging User Guide: https://packaging.python.org/en/latest/tutorials/packaging-projects/
- PyPI Trusted Publishing: https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/
- Add a Trusted Publisher: https://docs.pypi.org/trusted-publishers/adding-a-publisher/
