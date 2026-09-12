# AGENTS.md

## Purpose

This repository provides multilingual Mallet topic inference for Impresso
newspaper content. It wires the shared make-based cookbook helpers in
`cookbook/` to a concrete topic-assignment pipeline.

The main processing product is per-newspaper topic assignment JSONL output. The
pipeline reads linguistic-processing JSONL input, prepares language-specific
Mallet input, runs configured Mallet inferencers, and merges the assignments
back into unified Impresso topic output. Run-level aggregation can build YTDF
and DTCI topic products per language.

## Main Entry Points

- `Makefile`: top-level orchestration entry point.
- `cookbook/processing_topics.mk`: Make rules that run topic inference.
- `lib/mallet_topic_inferencer.py`: main topic inference script.
- `lib/linguistic_processing2mallet_text_input.py`: converts lingproc records to
  Mallet text input.
- `lib/mallet2topic_assignment_jsonl.py`: converts Mallet output to assignment
  JSONL.
- `lib/aggregate_topic_assignments.py`: builds run-level topic aggregates.
- `models/tm/`: Mallet inferencers, pipes, configs, vocabularies, and topic
  descriptions. Binary artifacts are tracked with Git LFS.
- `cookbook/`: shared Make/Python cookbook framework used by this project.

The `cookbook/AGENTS.md` file documents the reusable cookbook layer. Prefer
this root file for project-level guidance.

## Tooling And Environment

- Python 3.11 is expected.
- The project uses `pipenv`; local Python work should run inside the
  Pipenv-managed project `.venv/`.
- Use `.venv/bin/python` directly when it exists, or `pipenv run ...`. Pass
  `PYTHON=.venv/bin/python` to Make targets that invoke Python when you need to
  be explicit.
- Create the local environment with:
  `PIPENV_VENV_IN_PROJECT=1 python3.11 -m pipenv install`
- Verify `pipenv --venv` points at `./.venv`.
- Java is required for Mallet. The README documents `openjdk-17`.
- On macOS, use GNU Make via `remake` or `gmake`; `/usr/bin/make` is too old.
- Keep command examples and Makefile target names written as `make` in docs.
- S3 credentials come from environment variables or `.env`:
  `SE_ACCESS_KEY`, `SE_SECRET_KEY`, and `SE_HOST_URL`.

Primary Python dependencies are declared in `Pipfile` and duplicated in
`lib/pyproject.toml`. The project depends on spaCy 3.6, `jpype1`, `boto3`,
`smart-open[s3]`, and language models downloaded from GitHub URLs.

## Operational Model

- Inputs and outputs live on S3.
- Local files under `build.d/` are mostly stamps, logs, or transient outputs.
- Make targets use local stamp files to decide what should run.
- Topic processing discovers target years from local lingproc stamp files under
  the configured `LOCAL_PATH_LINGPROC`.
- `sync-input` includes `sync-lingproc` in this repo because lingproc output is
  the topic pipeline input.
- `sync-output` includes both `sync-lingproc` and `sync-topics`, so forced output
  resync can refresh local input stamps as well as topic-output stamps.
- `python3 -m impresso_cookbook.local_to_s3` is the normal upload helper. Do not
  replace it with raw `aws s3 cp` in recipes unless explicitly changing pipeline
  semantics.
- `.wip` objects are used to prevent concurrent workers from producing the same
  S3 target.

## Make Include Sanity

The root `Makefile` composes the project from cookbook fragments. When changing
targets or help text, verify that the fragment defining a target is actually
included by the root `Makefile`.

Do not duplicate cookbook-owned target lists in the root `help::` output. Target
help belongs next to the rule that defines the target, usually as `help-setup::`,
`help-sync::`, `help-processing::`, `help-orchestration::`, `help-clean::`, or
`help-aggregation::` in the corresponding included `cookbook/*.mk` file. If a
cookbook fragment is not included, its target-specific help should not appear.

Important root includes include:

- `cookbook/help.mk` for topic help.
- `cookbook/make_settings.mk` for strict Make/Shell behavior.
- `cookbook/setup.mk`, `cookbook/setup_python.mk`, `cookbook/setup_topics.mk`,
  and `cookbook/setup_aws.mk` for setup.
- `cookbook/local_to_s3.mk` for local/S3 path conversion helpers.
- `cookbook/newspaper_list.mk` before generated per-newspaper targets.
- `cookbook/paths_rebuilt.mk`, `cookbook/paths_langident.mk`,
  `cookbook/paths_lingproc.mk`, and `cookbook/paths_topics.mk` for path/run-ID
  variables.
- `cookbook/sync_lingproc.mk` and `cookbook/sync_topics.mk` for local S3 stamp
  synchronization.
- `cookbook/processing_topics.mk` for `topics-target`.
- `cookbook/aggregators_topics.mk` for `aggregate-topics` and `aggregate`.

If help advertises a target, run `remake <target> -n` or `remake <target>` for a
low-risk target to confirm the rule exists. On macOS, use `remake` or `gmake`,
not system `/usr/bin/make`.

For a concise inventory of active targets and descriptions, run `remake --tasks`
with the same `CFG=...` and variable overrides you would use for the real run.
Use this when checking documentation consistency against the current included
Make fragments.

## Important Make Variables

- `CFG`: selects a run-specific Make config.
- `NEWSPAPER`: selected newspaper prefix, often including provider.
- `NEWSPAPER_YEARS`: optional year scope. Collection entries in
  `PROVIDER/NEWSPAPER/YEAR` form set this automatically.
- `NEWSPAPER_HAS_PROVIDER`: whether newspaper IDs include a provider prefix.
- `NEWSPAPERS_TO_PROCESS_FILE`: list used by collection runs.
- `NEWSPAPER_JOBS`: parallel jobs within one newspaper.
- `COLLECTION_JOBS`: number of newspapers launched concurrently.
- `COLLECTION_TARGET`: target executed by collection runners, defaulting to
  `newspaper`.
- `MAX_LOAD`: load limit for Make/GNU parallel.
- `RUN_ID_LINGPROC`: input lingproc run identifier.
- `RUN_ID_TOPICS`: output topic run identifier.
- `TOPICS_LANGUAGES`: languages passed to the inferencer.
- `TOPICS_*_CONFIG`: language-specific model config files.
- `TOPICS_WIP_ENABLED`, `TOPICS_WIP_MAX_AGE`: S3 WIP coordination settings.

## Safe Working Rules

- Do not modify or commit secrets in `.env` or `.aws/credentials`.
- Treat untracked notebooks, sample JSONL files, compressed test inputs, model
  experiments, and local visualization scripts as user state unless explicitly
  told otherwise.
- Do not delete `build.d/`, S3 stamps, local sample data, topic outputs, or WIP
  markers as a cleanup step unless the user explicitly requests it.
- Preserve S3 path conventions, year scoping, and stamp-file behavior when
  editing Make rules.
- When editing Make fragments, keep the existing style: documented user
  variables, double-colon target extension, and help text for public targets.
- Do not rename or move model artifacts under `models/tm/` unless the task
  explicitly requires it.
- Avoid large generated-file diffs. Model binaries, pipes, inferencers, and lock
  files should usually remain untouched.
- Respect uncommitted user changes and work with them rather than reverting them.

## Practical Validation

Use the smallest checks that match the change:

```sh
.venv/bin/python -m py_compile lib/mallet_topic_inferencer.py lib/mallet2topic_assignment_jsonl.py
PYTHON=.venv/bin/python make help
PYTHON=.venv/bin/python make help-processing
PYTHON=.venv/bin/python make sync-output -n CFG=configs/config-topics-tm-mallet_infer_seed42_v3.0.0-multilingual_v3-0-0.mk NEWSPAPER=BNF/figaro1826 NEWSPAPER_YEARS=1826
```

On macOS, run Make commands through `remake` or `gmake`.

Full pipeline targets usually need live S3 credentials, network access, Java,
and large model/runtime setup, so avoid running them casually during
documentation or narrow code changes.
