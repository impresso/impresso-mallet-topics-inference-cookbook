# Getting Started with Impresso Mallet Topic Inference

Welcome! This guide is designed to help new users and contributors set up, understand, and run topic inference on historical newspaper data.

Whether you want to test models locally without cloud credentials or run full production pipelines against S3, this document walks you through each step.

---

## 1. Overview: What Does This Pipeline Do?

This project performs multilingual topic inference using Mallet LDA models on newspaper content processed by the Impresso project:

```
+----------------------------------------------------------------------------------+
| 1. Input: Linguistic Processing JSONL (tokenized, lemmatized, POS-tagged text)   |
+----------------------------------------------------------------------------------+
                                        |
                                        v
+----------------------------------------------------------------------------------+
| 2. Feature Filtering: Select UPOS tags (NOUN, PROPN), normalize lemmas & length  |
+----------------------------------------------------------------------------------+
                                        |
                                        v
+----------------------------------------------------------------------------------+
| 3. Mallet Vectorization: Text -> Mallet Pipe (language-specific vocabularies)    |
+----------------------------------------------------------------------------------+
                                        |
                                        v
+----------------------------------------------------------------------------------+
| 4. Mallet Inference: Pre-trained Mallet Inferencer generates topic distributions |
+----------------------------------------------------------------------------------+
                                        |
                                        v
+----------------------------------------------------------------------------------+
| 5. Output: Formatted Impresso Topic JSONL (topic IDs, probability scores)        |
+----------------------------------------------------------------------------------+
```

Supported languages include **French (`fr`)**, **German (`de`)**, **English (`en`)**, and **Luxembourgish (`lb`)**.

---

## 2. Environment & Prerequisites

### System Requirements
- **Python**: 3.11 (`pipenv` is used to manage dependencies)
- **Java**: OpenJDK 17 or newer (needed by Mallet & JPype)
- **GNU Make**: Version 4 or newer (`brew install make` on macOS)
- **Git LFS**: Required to pull pre-trained binary models, pipes, and vocabularies

### Step-by-Step Installation

#### macOS
```sh
# 1. Install system tools via Homebrew
brew install python@3.11 git git-lfs make coreutils parallel openjdk@17 ninja ant

# 2. Ensure JAVA_HOME is set in your environment
export JAVA_HOME=$(/usr/libexec/java_home -v 17)
# (Optional) add to ~/.zshrc or ~/.bash_profile:
# echo 'export JAVA_HOME=$(/usr/libexec/java_home -v 17)' >> ~/.zshrc
```

#### Ubuntu / Debian
```sh
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-distutils git git-lfs \
                    make moreutils coreutils parallel openjdk-17-jre-headless
```

### Python Virtual Environment Setup
```sh
# 1. Clone repository and initialize Git LFS
git lfs install
git clone --recursive https://github.com/impresso/impresso-mallet-topic-inference.git
cd impresso-mallet-topic-inference
git lfs pull  # IMPORTANT: pulls binary models and pipes in models/tm/

# 2. Install Python dependencies in project .venv/
PIPENV_VENV_IN_PROJECT=1 python3.11 -m pipenv install
```

---

## 3. Quickstart: 5-Minute Local Run (No S3 / No Credentials)

You do **not** need an S3 bucket or cloud credentials to test topic inference. A sample dataset is bundled directly in the repository:

```sh
# Run sample inference across German and French articles
make sample-run
```

Or run via the dedicated helper script:
```sh
./samples/run_sample.sh
```

### Checking the Results
The generated output is located at [`samples/sample_output_topics.jsonl`](./samples/sample_output_topics.jsonl).

Each line corresponds to an article with its assigned topic distribution:
```json
{
  "ci_id": "sample-doc-fr-001",
  "ts": "2026-11-06T15:54:05Z",
  "lg": "fr",
  "topic_count": 100,
  "topics": [
    {"t": "tm-fr-all-v3.0_tp04_fr", "p": 0.824},
    {"t": "tm-fr-all-v3.0_tp55_fr", "p": 0.023},
    {"t": "tm-fr-all-v3.0_tp21_fr", "p": 0.022}
  ],
  "min_p": 0.02,
  "topic_model_id": "tm-fr-all-v3.0",
  "model_id": "topics-v3.0.0-sample"
}
```

---

## 4. How the Data Formats Work

### Input Data (`lingproc` format)
Inputs to the topic inferencer are JSONL files containing linguistic processing results (sentences, tokenization, lemmatization, and Universal POS tags).

Key fields expected in each JSON line:
```json
{
  "id": "doc-identifier-123",
  "ts": "1826-01-15T00:00:00",
  "sents": [
    {
      "lg": "fr",
      "tok": [
        {"t": "Le", "l": "le", "p": "DET"},
        {"t": "gouvernement", "l": "gouvernement", "p": "NOUN"},
        {"t": "ministre", "l": "ministre", "p": "NOUN"}
      ]
    }
  ]
}
```

> **Preprocessing rules**: By default, the inferencer only extracts tokens where `p` is `NOUN` or `PROPN` (and length $\ge 3$). Articles with fewer than 8 eligible content tokens are excluded from inference.

### Topic Descriptions
Human-readable labels and top keywords for each topic are available in the model description files:
- `models/tm/tm-fr-all-v3.0.topic_model_topic_description.jsonl.bz2`
- `models/tm/tm-de-all-v3.0.topic_model_topic_description.jsonl.bz2`

---

## 5. Running Custom Files with the Python CLI

You can run `lib/mallet_topic_inferencer.py` directly on your own files:

```sh
.venv/bin/python -m lib.mallet_topic_inferencer \
  --input /path/to/my_lingproc.jsonl \
  --input-format impresso \
  --output /path/to/my_topics.jsonl \
  --languages fr de \
  --fr_config models/tm/tm-fr-all-v3.0.config.json \
  --de_config models/tm/tm-de-all-v3.0.config.json \
  --min-p 0.05 \
  --impresso-model-id custom-run-v1
```

Common arguments:
- `--input`: Path to input file (`.jsonl`, `.jsonl.bz2`, or `-` for stdin).
- `--output`: Destination file for topic assignments (`.jsonl` or `.jsonl.bz2`).
- `--languages`: List of languages to infer (`fr`, `de`, `en`, `lb`).
- `--<lang>_config`: Path to language config JSON defining the model, pipe, vocabulary, and token filters.
- `--min-p`: Minimum topic probability to include in output (default: `0.02`).

---

## 6. Production Pipelines with S3 and Make

When working in the Impresso cluster or S3 environment:

1. **Configure Credentials**:
   Copy `dotenv.sample` to `.env` and fill in your S3 credentials:
   ```sh
   cp dotenv.sample .env
   # Set SE_ACCESS_KEY, SE_SECRET_KEY, and SE_HOST_URL
   ```

2. **Select a Configuration File**:
   Run configurations live in `configs/`, e.g., `configs/config-topics-tm-mallet_infer_seed42_v3.0.0-multilingual_v3-0-0.mk`.

3. **Preview and Run a Newspaper**:
   ```sh
   CFG=configs/config-topics-tm-mallet_infer_seed42_v3.0.0-multilingual_v3-0-0.mk
   
   # Dry-run preview
   make newspaper -n CFG=$CFG NEWSPAPER=BNF/figaro1826 NEWSPAPER_YEARS=1826

   # Real processing
   make newspaper CFG=$CFG NEWSPAPER=BNF/figaro1826 NEWSPAPER_YEARS=1826
   ```

---

## 7. Troubleshooting & FAQ

* **JPype / Java JVM fails to start**:
  Ensure `JAVA_HOME` points to OpenJDK 17+. Test it with:
  ```sh
  .venv/bin/python lib/test_jpype_installation.py
  ```

* **Git LFS models not found or zero bytes**:
  If Mallet throws an EOF or serialization exception when loading `.pipe` or `.inferencer`:
  ```sh
  git lfs pull
  ```

* **macOS Make version error (`GNU Make 4+ required`)**:
  Default macOS make is GNU Make 3.81. Install GNU Make via Homebrew (`brew install make`) and run using `gmake` or place `/usr/local/opt/make/libexec/gnubin` (or `/opt/homebrew/opt/make/libexec/gnubin`) in your `PATH`.

* **Smart-open and SpaCy conflicts**:
  Ensure dependencies are installed through the locked Pipfile (`PIPENV_VENV_IN_PROJECT=1 python3.11 -m pipenv install`). The project requires `smart-open==6.4`.
