gen:
	docker run --rm -v ${PWD}:/local openapitools/openapi-generator-cli:v7.7.0 generate \
	  -i /local/openapi/marketplace.yaml \
	  -g python-fastapi \
	  -o /local/generated \
	  --additional-properties=packageName=generated,generateSourceCodeOnly=true