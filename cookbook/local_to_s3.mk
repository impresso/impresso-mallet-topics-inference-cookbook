$(call log.debug, COOKBOOK BEGIN INCLUDE: cookbook/local_to_s3.mk)


# function to turn a local file path into a s3 file path, optionall cutting off the
# suffix given as argument
define local_to_s3
$(subst $(2),,$(subst $(BUILD_DIR),s3:/,$(1)))
endef


# Target to test the local_to_s3 function
test-local_to_s3:
	@echo "Running tests for local_to_s3 function..."
	@echo "Test 1: Convert local path to S3 path without stripping any suffix"
	@echo "Input: build.d/22-rebuilt-final/marieclaire/file.txt"
	@echo "Expected Output: s3://22-rebuilt-final/marieclaire/file.txt"
	@echo "Actual Output  : $(call local_to_s3,build.d/22-rebuilt-final/marieclaire/file.txt)"
	@echo
	@echo "Test 2: Convert local path to S3 path and strip the .txt suffix"
	@echo "Input: build.d/22-rebuilt-final/marieclaire/file.txt, .txt"
	@echo "Expected Output: s3://22-rebuilt-final/marieclaire/file"
	@echo "Actual Output  : $(call local_to_s3,build.d/22-rebuilt-final/marieclaire/file.txt,.txt)"
	@echo
	@echo "Test 3: Convert local path to S3 path and strip a custom suffix"
	@echo "Input: build.d/22-rebuilt-final/marieclaire/file.custom, .custom"
	@echo "Expected Output: s3://22-rebuilt-final/marieclaire/file"
	@echo "Actual Output  : $(call local_to_s3,build.d/22-rebuilt-final/marieclaire/file.custom,.custom)"
	@echo



$(call log.debug, COOKBOOK END INCLUDE: cookbook/local_to_s3.mk)
