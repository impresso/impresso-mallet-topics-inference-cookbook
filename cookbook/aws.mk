
test-aws: |.aws/credentials .aws/config
	AWS_CONFIG_FILE=.aws/config AWS_SHARED_CREDENTIALS_FILE=.aws/credentials \
	aws s3 ls s3://41-processed-data-staging/lingproc/lingproc-pos-spacy_v3.6.0-multilingual_v1-0-3/

create-aws-config: .aws/credentials .aws/config

.aws/config: | .env
	@echo "Creating local AWS CLI configuration: $@"
	mkdir -p .aws
	@echo "[default]" > .aws/config
	@echo "region = us-east-1" >> .aws/config
	@echo "output = json" >> .aws/config
	@echo "endpoint_url = $$(grep SE_HOST_URL .env | cut -d '=' -f2)" >> .aws/config


.aws/credentials: | .env
	@echo "Creating local AWS CLI configuration: $@"
	echo "[default]" > .aws/credentials
	@echo "aws_access_key_id = $$(grep SE_ACCESS_KEY .env | cut -d '=' -f2)" >> .aws/credentials
	@echo "aws_secret_access_key = $$(grep SE_SECRET_KEY .env | cut -d '=' -f2)" >> .aws/credentials
	