# Release 3.0.0

Stable release for the normalized-lemma v3 topic inference bundle.

## What Changed

- added v3 topic model artifacts for German, French, English, and Luxembourgish
- added per-language v3 configs under `models/tm/`
- added character-normalization tables and normalized lemma vocabularies for each v3 language
- added the reproducible run config `configs/config-topics-tm-mallet_infer_seed42_v3.0.0-multilingual_v3-0-0.mk`
- added support for `schema_version: "3.0"` and `preprocessing.mode: "normalized-lemma-vocab-v1"`
- vendored the MALLET 2.1.0 runtime under `mallet-2.1.0/`
- added runtime selection based on model config metadata
- added schema caching for topic-assignment JSON schema validation
- improved logging, error handling, and direct S3 input support in the inference path
- updated README, Makefile help, and release guidance to use the v3 config as the current example

## v3 Model Behavior

The v3 models use normalized lemma vocabularies rather than legacy token-to-lemma
lookup files. For v3 inference, the pipeline reads input lemmas, applies the
model-specific `*.char-normalization.json`, filters against `*.vocab.tsv.bz2`,
and preserves the v3 training-time UPOS filters.

The v3 bundle includes:

- `tm-de-all-v3.0`
- `tm-fr-all-v3.0`
- `tm-en-all-v3.0`
- `tm-lb-all-v3.0`

## Runtime Behavior

- v3 models require MALLET 2.1.0
- v3 vectorization uses `--use-pipe-from-without-rewrite`, so model pipe files are not rewritten during inference
- cookbook sync creates local per-file stamps, while the topic inferencer reads the corresponding input files directly from S3
- topic-output S3 behavior remains controlled by `cookbook/processing_topics.mk`, including dry-run, WIP locks, skip-if-output-exists, overwrite, and timestamp-only local outputs

## Breaking Changes

- v3 runs require MALLET 2.1.0
- v3 runs expect lingproc input from `lingproc-pos-spacy_v3.6.0-multilingual_v1-0-3`
- v3 models use normalized lemma vocabularies and do not require `*.vocab.lemmatization.tsv.gz` artifacts

## Setup And Usage

Python remains pinned to Python 3.11. Java is required for MALLET and JPype.
Large model and runtime artifacts are tracked with Git LFS:

```bash
git lfs pull
```

Use the v3 run configuration:

```bash
make newspaper NEWSPAPER=<TITLE> \
  CFG=configs/config-topics-tm-mallet_infer_seed42_v3.0.0-multilingual_v3-0-0.mk
```

For a local dry-run without S3 topic writes:

```bash
make newspaper NEWSPAPER=<TITLE> \
  CFG=configs/config-topics-tm-mallet_infer_seed42_v3.0.0-multilingual_v3-0-0.mk \
  TOPICS_DRY_RUN_OPTION=--s3-output-dry-run
```

## Validation

- verified Python syntax for the inference modules
- verified all v3 config-declared artifacts exist locally
- ran a `BNL/luxwort` v3 `lb` smoke test for `luxwort-1848` with local topic output and no S3 topic writes
- verified MALLET 2.1.0 vectorization uses `--use-pipe-from-without-rewrite` for v3 model pipes

## Known Issues

- running cookbook targets requires valid S3 credentials for real input sync and S3-backed inference input
- on macOS, the system `make` may be too old; use a GNU Make 4+ command
- v3 output quality depends on input compatibility with the expected lingproc run family

# Release 2.0.1

Initial tagged release of `impresso-mallet-topic-inference`.

## What Changed

- packaged the repository as a standalone topic inference project
- added Make-based orchestration for setup, sync, processing, and cleanup
- added multilingual Mallet topic inference for Impresso lingproc input
- improved macOS setup guidance, including GNU Make and Java requirements
- clarified the separation between the inferencer and surrounding S3 orchestration logic
- updated cookbook integration to the submodule state used by this release

## Setup And Usage

- Python 3.11 is required
- GNU Make 4+ is required
- Java is required for the Mallet runtime
- `spacy==3.6.0` requires `smart-open<7.0.0,>=5.2.1`

## Notes

- release tag: `v2.0.1`
- tagged commit: `3e2191f`
