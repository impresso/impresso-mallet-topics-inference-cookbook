# Release Notes: v2.0.1

Release Date: 2026-04-22  
Tag: v2.0.1

## Overview

`v2.0.1` is the first tagged release of `impresso-mallet-topic-inference`.
It packages the Make-based orchestration, multilingual Mallet topic inference,
and repository-specific setup/configuration needed to run the topics pipeline.

## Highlights

- Initial public release of the repository as a standalone topics inference project.
- Make-based orchestration for setup, sync, processing, and cleanup.
- Multilingual topic inference pipeline for Impresso lingproc input.
- Improved macOS setup guidance, including GNU Make and Java requirements.
- Clearer separation of concerns between the inferencer and surrounding S3 orchestration logic.
- Updated cookbook integration to the latest submodule state used by this release.

## Notes

- This repository requires Python 3.11.
- GNU Make 4+ is required; macOS users will typically need Homebrew `make`/`gmake`.
- `spacy==3.6.0` requires `smart-open<7.0.0,>=5.2.1`.

## Reference

Tagged commit: `3e2191f`
