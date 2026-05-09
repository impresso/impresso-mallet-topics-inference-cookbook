# Release Process Guide

This document describes the process for creating and publishing releases for the impresso-mallet-topic-inference project.

## Table of Contents

- [Release Workflow](#release-workflow)
- [Version Numbering](#version-numbering)
- [Preparing a Release](#preparing-a-release)
- [Updating RELEASE.md](#updating-releasemd)
- [Publishing a Release](#publishing-a-release)
- [Post-Release Tasks](#post-release-tasks)

## Release Workflow

### Overview

Releases follow these general steps:

1. **Prepare**: Review changes, update documentation, and test
2. **Document**: Update `RELEASE.md`, which serves as both changelog and release notes
3. **Commit**: Commit `RELEASE.md` and any final version/documentation updates
4. **Tag**: Create a git tag for that exact release commit
5. **Publish**: Create a GitHub release from the committed `RELEASE.md` file
6. **Announce**: Notify users and update installation instructions

The key rule is to avoid writing or revising release notes after the release tag has
already been created. `RELEASE.md` should be part of the tagged commit so
that the repository state, the tag, and the published GitHub release all refer to the
same snapshot. Do not maintain a separate `CHANGELOG.md`; integrate changelog-style
"what changed" entries directly into `RELEASE.md`.

## Version Numbering

This project follows [Semantic Versioning](https://semver.org/) (SemVer):

```
MAJOR.MINOR.PATCH
```

- **MAJOR**: Incompatible API changes or breaking changes
- **MINOR**: New features, backwards-compatible
- **PATCH**: Bug fixes, backwards-compatible

### Examples

- `1.0.0` → `2.0.0`: Breaking change (e.g., removed support for Python 3.10)
- `1.0.0` → `1.1.0`: New feature (e.g., added topic modeling pipeline)
- `1.0.0` → `1.0.1`: Bug fix (e.g., fixed S3 synchronization issue)

### Pre-release Versions

Pre-release versions can be tagged with additional labels:

- `1.1.0-alpha.1`: Early testing version
- `1.1.0-beta.1`: Feature-complete, testing phase
- `1.1.0-rc.1`: Release candidate, final testing

## Preparing a Release

### 1. Review Changes

```bash
# Compare with the last release tag
git log v1.0.0..HEAD --oneline

# Review file changes
git diff v1.0.0..HEAD --stat

# Check what's changed in specific areas
git log v1.0.0..HEAD --oneline -- lib/
git log v1.0.0..HEAD --oneline -- "*.mk"
```

### 2. Update Documentation

- [ ] Update `RELEASE.md` with all changes since the last release
- [ ] Update `README.md` if there are new features or changes to usage
- [ ] Review and update any outdated documentation
- [ ] Ensure all new features have documentation

### 3. Update Version References

Check and update version references in:

- [ ] `README.md` (usage examples, config file names)
- [ ] `AGENT.md` (example config filenames)
- [ ] Config filenames under `configs/` (the version is embedded in `MODEL_VERSION_TOPICS` / `RUN_VERSION_TOPICS`)

### 4. Test the Release

Run a smoke test to verify the pipeline environment end-to-end:

```bash
# Verify Python/Java environment
make setup

# Check that the Python installation and JPype are ready
make check-python-installation

# Dry-run inference for a single newspaper (no S3 writes)
make newspaper NEWSPAPER=<TITLE> \
  CFG=configs/config-topics-tm-mallet_infer_seed42_v3.0.0-multilingual_v3-0-0.mk \
  TOPICS_DRY_RUN_OPTION=--s3-output-dry-run \
  LOGGING_LEVEL=DEBUG
```

## Updating RELEASE.md

`RELEASE.md` is the canonical release history for this repository. It combines the
changelog and release notes in one reverse-chronological file, with the newest release
first. Update it before the tag is created and commit it together with the final
release-ready changes. The GitHub release description should then be created from
that committed content instead of being written separately in the web interface.

### Structure

Each release entry should include:

1. **Overview**: Brief summary of the release
2. **Major Features**: Significant new functionality
3. **Technical Improvements**: Behind-the-scenes improvements
4. **Bug Fixes**: Issues resolved
5. **Breaking Changes**: Anything that breaks compatibility
6. **Migration Guide**: How to upgrade from previous version
7. **Known Issues**: Any known problems or limitations
8. **Dependencies**: New or updated dependencies
9. **Contributors**: People who contributed to this release

### Template

Use this template structure at the top of `RELEASE.md`:

````markdown
# Release X.Y.Z

Short release summary.

## What Changed

- Change 1
- Change 2

## Runtime Behavior

- Runtime or model behavior notes

## Breaking Changes

- Breaking change and migration path

## Setup And Usage

```bash
make ...
```

## Known Issues

- Known issue
````

### Generating Change Lists

Use git to generate lists of changes:

```bash
# List all commits
git log v1.0.0..HEAD --oneline

# Group by component
git log v1.0.0..HEAD --oneline -- lib/
git log v1.0.0..HEAD --oneline -- models/tm/
git log v1.0.0..HEAD --oneline -- configs/
git log v1.0.0..HEAD --oneline -- cookbook/

# Get commit authors
git shortlog v1.0.0..HEAD -sn

# Get file statistics
git diff v1.0.0..HEAD --stat

# List new files
git diff v1.0.0..HEAD --name-status | grep "^A"

# List modified files
git diff v1.0.0..HEAD --name-status | grep "^M"
```

## Publishing a Release

### 1. Commit Release Notes and Final Metadata

Before tagging, ensure `RELEASE.md` and any final documentation or version updates
are committed:

```bash
git add README.md AGENT.md RELEASE.md
git add configs/
git commit -m "Prepare release v1.1.0"
```

This ensures `RELEASE.md` is part of the exact commit that will be tagged.

### 2. Create Git Tag

> **Note:** The tag should land on `main`. If you have been working on a
> `version-X.Y` dev branch, merge it to `main` before tagging (or immediately
> after, then re-tag on the resulting merge commit):
>
> ```bash
> git checkout main
> git merge --no-ff version-X.Y -m "Merge version-X.Y into main for release vX.Y.Z"
> ```

```bash
# Create an annotated tag (on main)
git tag -a v1.1.0 -m "Release v1.1.0: Description"

# Push the branch and tag together
git push origin main v1.1.0
```

### 3. Create GitHub Release

#### Via GitHub Web Interface

1. Go to https://github.com/impresso/impresso-mallet-topic-inference/releases
2. Click "Draft a new release"
3. Select the tag you just created
4. Fill in the release title: `v1.1.0` or descriptive name
5. Paste the relevant top section from the committed `RELEASE.md` file into the description
6. Check "Set as a pre-release" if applicable
7. Click "Publish release"

#### Via GitHub CLI

```bash
# Install gh CLI if needed
# brew install gh  # macOS
# apt install gh   # Ubuntu

# Authenticate
gh auth login

tmp_notes=/tmp/impresso-mallet-topic-inference-v1.1.0-release.md
awk '/^# Release / && seen { exit } /^# Release / { seen=1 } seen { print }' RELEASE.md > "$tmp_notes"

# Create release from the extracted top entry in RELEASE.md
gh release create v1.1.0 \
  --title "v1.1.0: Description" \
  --notes-file "$tmp_notes" \
  --prerelease  # omit for stable release
```

Using `--notes-file` is preferred because it makes the GitHub release text come from
the same committed `RELEASE.md` content. Since `RELEASE.md` contains multiple
releases, paste only the relevant top section in the web interface or use a temporary
extracted notes file when using the CLI.

### 4. Update Existing Release (if needed)

If you need to improve release notes for an existing release:

```bash
# Update release notes
tmp_notes=/tmp/impresso-mallet-topic-inference-v1.1.0-release.md
awk '/^# Release / && seen { exit } /^# Release / { seen=1 } seen { print }' RELEASE.md > "$tmp_notes"

gh release edit v1.1.0 \
  --notes-file "$tmp_notes"

# Or via web interface:
# Go to the release page and click "Edit release"
```

This should be treated as a correction path, not the normal workflow. The normal path
is to finalize and commit `RELEASE.md` before creating the tag.

## Post-Release Tasks

### 1. Update Main Branch

If the dev branch was not merged before tagging, merge it now and push:

```bash
git checkout main
git merge --no-ff version-X.Y -m "Merge version-X.Y into main for release vX.Y.Z"
git push origin main version-X.Y
```

### 2. Verify Configs Point to Released Model IDs

Confirm that the configs under `configs/` reference the correct `MODEL_VERSION_TOPICS`
and `RUN_VERSION_TOPICS`, and that the matching per-language model configs under
`models/tm/` exist and are correctly named.

### 3. Announce Release

- [ ] Notify team members
- [ ] Update any downstream pipeline configs that reference this inference run ID

### 4. Monitor for Issues

After release:

- Monitor GitHub issues for bug reports
- Check discussion forums or communication channels
- Be prepared to create patch releases if critical bugs are found

## Hotfix Releases

For critical bug fixes:

1. Create a hotfix branch from the release tag:

   ```bash
   git checkout -b hotfix/1.1.1 v1.1.0
   ```

2. Make the fix and test thoroughly

3. Create a patch release:

   ```bash
   git tag -a v1.1.1 -m "Hotfix: Description of critical fix"
   git push origin v1.1.1
   ```

4. Add the hotfix notes to the top of `RELEASE.md` and create the release from that entry

5. Merge hotfix back to main:
   ```bash
   git checkout main
   git merge --no-ff hotfix/1.1.1
   git push origin main
   ```

## Checklist

Use this checklist when preparing a release:

- [ ] All tests pass
- [ ] Documentation is updated
- [ ] `RELEASE.md` is updated with the newest release first
- [ ] Version numbers are updated where needed
- [ ] `RELEASE.md` includes both changelog and release-note content
- [ ] `RELEASE.md` is committed on the release commit
- [ ] Dev branch merged to `main` and tag is on `main`
- [ ] Git tag is created
- [ ] GitHub release is created from the committed `RELEASE.md` content
- [ ] The new `RELEASE.md` entry follows the template
- [ ] Installation instructions are verified
- [ ] Team is notified
- [ ] Known issues are documented

## Tools and Resources

- **GitHub CLI**: https://cli.github.com/
- **Semantic Versioning**: https://semver.org/
- **Git Tagging**: https://git-scm.com/book/en/v2/Git-Basics-Tagging

## Questions?

If you have questions about the release process, please:

- Review previous releases for examples
- Check this guide
- Ask the maintainers

---

**Last Updated:** May 8, 2026
