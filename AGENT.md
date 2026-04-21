# AGENT.md

This repository provides multilingual topic inference for Impresso newspaper content. The main execution surface is GNU Make, with Python scripts in `lib/` and Mallet runtime assets in `mallet/` and `models/tm/`.

## What This Repo Does

- Reads multilingual input content.
- Detects or uses language information to split processing by language.
- Vectorizes content with language-specific Mallet pipes.
- Runs topic inference with language-specific inferencers.
- Merges per-language outputs back into unified topic assignment data.

See [Readme.md](./Readme.md) for the pipeline overview and [cookbook/README.md](./cookbook/README.md) for the Make-based processing model.

## Important Directories

- `lib/`: Python entry points and helper modules used by the pipeline.
- `models/tm/`: Mallet inferencers, pipes, configs, vocabularies, and topic descriptions.
- `mallet/`: bundled Mallet runtime jars and launcher.
- `cookbook/`: included Make fragments documenting setup, sync, and processing targets.
- `build.d/`: default local working directory created by the Make workflow. Safe to recreate.

## Environment

- Python: `3.11`
- Package manager: `pipenv`
- Java runtime: required for Mallet (`openjdk-17` is documented in the README)
- Common CLI tools used by setup/docs: `make`, `git`, `git-lfs`, `parallel`, `coreutils`, `moreutils`

Primary Python dependencies are declared in `Pipfile` and duplicated in `lib/pyproject.toml`. The project depends on spaCy 3.6, `jpype1`, `boto3`, `smart-open[s3]`, and language models downloaded from GitHub URLs.

## Setup Commands

Typical local setup:

```sh
python3.11 -m pip install pipenv
python3.11 -m pipenv install
python3.11 -m pipenv shell
```

The Make-based bootstrap path is:

```sh
make setup
```

That setup delegates into `cookbook/setup.mk`, `cookbook/setup_python.mk`, and `cookbook/setup_topics.mk`.

## Main Entry Points

Top-level help:

```sh
make
make help
remake --tasks
```

Main Make targets:

- `make setup`: prepare local directories and language/model prerequisites.
- `make newspaper`: run sync plus processing for a single newspaper.
- `make all`: sync fresh data, then process in parallel.
- `make collection`: process multiple newspapers with GNU parallel.

The top-level `Makefile` is mostly an orchestrator that includes fragments from `cookbook/`.

## Local Configuration

- Local overrides belong in `config.local.mk`.
- Do not commit `config.local.mk`.
- Secrets and S3 credentials are expected via environment variables or a local `.env`, based on `dotenv.sample`.
- `SE_ACCESS_KEY` and `SE_SECRET_KEY` are referenced by the cookbook documentation for S3 access.

## Agent Working Rules

- Prefer changing the smallest possible surface area.
- Treat the Make workflow as the source of truth for execution order and operational behavior.
- When changing pipeline behavior, inspect the relevant included Make fragments under `cookbook/`, not only the root `Makefile`.
- Keep Python compatibility at 3.11 unless the repository is intentionally being upgraded.
- Do not rename or move model artifacts under `models/tm/` unless the task explicitly requires it.
- Avoid large generated-file diffs. Model binaries, pipes, and inferencers should usually remain untouched.
- Respect uncommitted user changes. At the time this guide was added, the worktree already contained unrelated modifications.

## Verification

There is no obvious dedicated automated test suite in the repository root. For changes, prefer verification proportional to the edit:

- For documentation-only changes: check Markdown rendering and referenced paths/commands.
- For Python changes: run targeted import or syntax validation where possible.
- For Make changes: run `make help` or the smallest safe target that exercises the edited logic.

If full execution would require network access, S3 credentials, or large model/runtime setup, say so explicitly instead of guessing.

## Files Worth Reading Before Larger Changes

- [Makefile](./Makefile)
- [Readme.md](./Readme.md)
- [cookbook/README.md](./cookbook/README.md)
- [cookbook/setup.mk](./cookbook/setup.mk)
- [cookbook/main_targets.mk](./cookbook/main_targets.mk)
- `cookbook/processing*.mk` and `cookbook/sync*.mk` for pipeline behavior
- relevant Python scripts in `lib/` for data format or inference logic
