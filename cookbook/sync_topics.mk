$(call log.debug, COOKBOOK BEGIN INCLUDE: cookbook/sync_topics.mk)



# Sync  the data from the S3 bucket to the local directory for input of textembeddings and output of textembeddings
sync: sync-input sync-output

PHONY_TARGETS += sync

### SYNCING THE INPUT DATA FROM S3 TO LOCAL DIRECTORY

IN_LOCAL_PROCESSED_DATA_LINGPROC_LAST_SYNCED_FILE := $(IN_LOCAL_PATH_PROCESSED_DATA_LINGPROC).last_synced
  $(call log.debug, OUT_LOCAL_PROCESSED_DATA_TOPICS_LAST_SYNCED_FILE)

sync-input: $(IN_LOCAL_PROCESSED_DATA_LINGPROC_LAST_SYNCED_FILE)

PHONY_TARGETS += sync-input


# the suffix of for the local stamp files (added to the input paths on s3)
IN_LOCAL_LINGPROC_STAMP_SUFFIX ?= ''
  $(call log.debug, IN_LOCAL_LINGPROC_STAMP_SUFFIX)

# Rule to sync the input data from the S3 bucket to the local directory
$(IN_LOCAL_PROCESSED_DATA_LINGPROC_LAST_SYNCED_FILE):
	# Syncing the processed data: 
	# From:  $(IN_S3_PATH_PROCESSED_DATA_LINGPROC)
	# To  :  $(IN_LOCAL_PATH_PROCESSED_DATA_LINGPROC)
	mkdir -p $(@D) && \
	python lib/s3_to_local_stamps.py \
	   $(IN_S3_PATH_PROCESSED_DATA_LINGPROC) \
	   --local-dir $(BUILD_DIR) \
	   --stamp-extension $(IN_LOCAL_LINGPROC_STAMP_SUFFIX) \
	   2> >(tee $@.log >&2) && \
	touch $@

     $(call log.debug, LINGPROC SYNC STAMP FILE: $(IN_LOCAL_PATH_PROCESSED_DATA_LINGPROC).last_synced)

# he local per-newspaper synchronization file stamp for the output text embeddings: What is on S3 has been synced?
OUT_LOCAL_PROCESSED_DATA_TOPICS_LAST_SYNCED_FILE := $(OUT_LOCAL_PATH_PROCESSED_DATA_TOPICS).last_synced
  $(call log.debug, OUT_LOCAL_PROCESSED_DATA_TOPICS_LAST_SYNCED_FILE)

clean-sync-input:
	rm -vf $(IN_LOCAL_PROCESSED_DATA_LINGPROC_LAST_SYNCED_FILE) || true
	rm -rfv $(IN_LOCAL_PATH_PROCESSED_DATA_LINGPROC) || true

PHONY_TARGETS += clean-sync-input


#### SYNCING THE OUTPUT DATA FROM S3 TO LOCAL DIRECTORY
sync-output: $(OUT_LOCAL_PROCESSED_DATA_TOPICS_LAST_SYNCED_FILE)

PHONY_TARGETS += sync-output

# the suffix of for the local stamp files (added to the input paths on s3)
OUT_LOCAL_TOPICS_STAMP_SUFFIX ?= ''
  $(call log.debug, OUT_LOCAL_TOPICS_STAMP_SUFFIX)

# Rule to sync the output data from the S3 bucket to the local directory
$(OUT_LOCAL_PROCESSED_DATA_TOPICS_LAST_SYNCED_FILE):
	mkdir -p $(@D) && \
	python lib/s3_to_local_stamps.py \
	   $(OUT_S3_PATH_PROCESSED_DATA_TOPICS) \
	   --local-dir $(BUILD_DIR) \
	   --stamp-extension $(OUT_LOCAL_TOPICS_STAMP_SUFFIX) \
	   2> >(tee $@.log >&2) && \
	touch $@


### CLEANING THE SYNC OUTPUT

clean-sync-output:
	rm -vf $(OUT_LOCAL_PROCESSED_DATA_TOPICS_LAST_SYNCED_FILE) || true
	rm -rfv $(OUT_LOCAL_PATH_PROCESSED_DATA_TOPICS) || true


PHONY_TARGETS += clean-sync-output


resync-output: clean-sync-output
	$(MAKE) sync-output

PHONY_TARGETS += resync-output


resync-input: clean-sync-input
	$(MAKE) sync-input

PHONY_TARGETS += resync-input

# Remove the local synchronization file stamp and redoes everything, ensuring a full sync with the remote server.
resync: resync-input resync-output

PHONY_TARGETS += resync



$(call log.debug, COOKBOOK END INCLUDE: cookbook/sync_topics.mk)
