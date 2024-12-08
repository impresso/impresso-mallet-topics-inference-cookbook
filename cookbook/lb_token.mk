## more tasks that are normally not used
LINGPROC_S3_PATH ?= s3://42-processed-data-final/lingproc/lingproc-pos-spacy_v3.6.0-multilingual_v1-0-3/
parallel-s3-compress:
	mkdir -p build.d/lb/ && \
	python3 lib/s3_to_local_stamps.py --list-files --list-files-glob '*.bz2' $(LINGPROC_S3_PATH) \
	 | shuf \
	 | parallel --eta 'output_file=lb/{= s:.*/::; s:\.jsonl\.bz2$$:.tsv:; =}; python3 lib/token_extractor.py --pos-tags NOUN --languages lb --output $$output_file {}'

compute-freq-dist:
	python3 lib/compute_freq_dist.py --input-dir lb/ --output-json lb.d/lb_freq_dist.json --output-tsv lb.d/lb.tsv

filter-tokens:
	python3 lib/filter_tokens.py --freq-json lb.d/lb_freq_dist.json --input-tsv lb.d/lb.tsv --output-tsv lb.d/lb.txt
