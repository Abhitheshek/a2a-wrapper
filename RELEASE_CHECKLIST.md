# Release Checklist

Use this checklist before publishing `a2a-wrapper`.

## Package

- [ ] `pyproject.toml` version is correct
- [ ] `src/a2a_wrapper/__init__.py` version is correct
- [ ] placeholder GitHub URLs in `pyproject.toml` are replaced
- [ ] `README.md` is up to date
- [ ] `DOCS.md` is up to date
- [ ] `FULL_PROJECT.md` is up to date

## Verification

- [ ] `pytest` passes
- [ ] `python -m build --no-isolation` succeeds
- [ ] built files exist in `dist/`
- [ ] package installs locally from the built wheel

## GitHub

- [ ] code pushed to GitHub
- [ ] `.github/workflows/ci.yml` exists
- [ ] `.github/workflows/publish.yml` exists
- [ ] GitHub environment `pypi` exists if needed

## PyPI

- [ ] PyPI account created
- [ ] project name `a2a-wrapper` is available or confirmed
- [ ] PyPI project created
- [ ] Trusted Publisher added for GitHub repo and `publish.yml`

## Release

- [ ] commit final changes
- [ ] push default branch
- [ ] create release tag, for example `v0.2.0`
- [ ] push tag
- [ ] confirm GitHub Actions publish job succeeds

## Post-release

- [ ] test install with `pip install a2a-wrapper`
- [ ] verify import works:

```python
from a2a_wrapper import AgentClient, AgentServerConfig, AgentCapability, create_agent_server
```
