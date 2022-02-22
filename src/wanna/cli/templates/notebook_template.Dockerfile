############ THIS FILE IS GENERATED, DO NOT EDIT ############

# Extend a GCP notebook image with our python libs
FROM {{ base_image }}

# Install pip requirements
COPY {{ requirements_txt }} .
RUN pip install -r requirements.txt --index-url "https://artifactory.ida.avast.com/artifactory/api/pypi/pypi-remote/simple/" --extra-index-url "https://artifactory.ida.avast.com/artifactory/api/pypi/pypi-local/simple/" --no-warn-script-location


