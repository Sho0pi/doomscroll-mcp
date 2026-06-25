# Releasing

Releases publish to PyPI automatically when you push a `vX.Y.Z` tag.

## One-time setup (maintainer, on pypi.org)

PyPI Trusted Publishing means no API tokens or secrets — GitHub authenticates
to PyPI over OIDC. Set it up once:

1. Create the project on PyPI (or reserve the name with a first manual upload):
   `uv build && uv publish` once with a token, **or** configure a *pending*
   trusted publisher before the first release.
2. On PyPI → the project → **Settings → Publishing → Add a trusted publisher**:
   - Owner: `Sho0pi`
   - Repository: `doomscroll-mcp`
   - Workflow name: `release.yml`
   - Environment: `pypi`
3. In the GitHub repo → **Settings → Environments → New environment** named
   `pypi` (the release job runs in it; add reviewers there if you want a manual
   approval gate before publish).

## Cutting a release

```bash
# 1. Bump the version (single source of truth)
#    edit pyproject.toml  [project] version = "0.2.0"

# 2. Move the CHANGELOG [Unreleased] items under a new [0.2.0] heading

# 3. Commit, tag, push
git commit -am "release: v0.2.0"
git tag v0.2.0
git push origin master --tags
```

The `release.yml` workflow then:
- verifies the tag matches the pyproject version (fails otherwise),
- `uv build` (wheel + sdist),
- `uv publish` to PyPI via OIDC,
- creates a GitHub Release with auto-generated notes and the built artifacts.

Versioning follows [SemVer](https://semver.org/): patch for fixes, minor for
new tools/params, major for breaking changes to the tool surface or reel shape.
