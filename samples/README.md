# Sample Topic Inference Data

This folder provides a minimal, self-contained dataset to test and explore multilingual Mallet topic inference **locally without S3 credentials or cloud storage**.

## Files in this Directory

- `sample_lingproc.jsonl`: Linguistic processing input format with tokenized, lemmatized, and PoS-tagged text for sample French and German articles.
- `sample_output_topics.jsonl`: Expected topic assignment output produced by `mallet_topic_inferencer.py`.
- `run_sample.sh`: Shell helper script to run the sample inference end-to-end.

## Running the Sample

### Option 1: Using Make (Recommended)

```sh
make sample-run
```

Or specify your Python binary explicitly if needed:
```sh
PYTHON=.venv/bin/python make sample-run
```

### Option 2: Using the Shell Script

```sh
./samples/run_sample.sh
```

### Option 3: Using the Python CLI Directly

```sh
.venv/bin/python -m lib.mallet_topic_inferencer \
  --input samples/sample_lingproc.jsonl \
  --input-format impresso \
  --output samples/sample_output_topics.jsonl \
  --languages fr de \
  --fr_config models/tm/tm-fr-all-v3.0.config.json \
  --de_config models/tm/tm-de-all-v3.0.config.json \
  --impresso-model-id topics-v3.0.0-sample
```

## Schema Summary

### Input (`sample_lingproc.jsonl`)

Each line is a JSON object with:
- `id` (string): Unique document / content item identifier.
- `ts` (string): Timestamp in ISO format.
- `sents` (array): Sentences, each containing:
  - `lg` (string): Sentence language code (`fr`, `de`, `en`, `lb`).
  - `tok` (array): Tokens with:
    - `t` (string): Surface token text.
    - `l` (string): Lemma (can be omitted if identical to `t`).
    - `p` (string): Universal Part of Speech tag (e.g. `NOUN`, `PROPN`, `VERB`, `ADJ`).

> **Note on Preprocessing Filters**: The v3 topic models by default require at least 8 eligible lemmas (`NOUN` or `PROPN` by default) in the document for it to be inferred. Documents with fewer content tokens are skipped by the reader.

### Output (`sample_output_topics.jsonl`)

Each line is a JSON object with:
- `ci_id` (string): Content item ID.
- `ts` (string): UTC timestamp of inference.
- `lg` (string): Detected/inferred document language.
- `topic_count` (int): Total number of topics in the model (e.g., 100).
- `topic_model_id` (string): Language model identifier (e.g., `tm-fr-all-v3.0`).
- `model_id` (string): Impresso run model ID.
- `min_p` (float): Minimum probability threshold applied (default `0.02`).
- `topics` (array): Array of assigned topics sorted by probability:
  - `t` (string): Topic identifier (e.g., `tm-fr-all-v3.0_tp04_fr`).
  - `p` (float): Topic probability weight for this document.
