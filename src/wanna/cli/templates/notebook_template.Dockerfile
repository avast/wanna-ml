############ THIS FILE IS GENERATED, DO NOT EDIT ############

# Extend a GCP notebook image with our python libs
FROM {{ base_image }}

# Install pip requirements
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
