FROM python:3.8.13-slim

# Install gcloud
RUN apt-get update && apt-get install apt-transport-https ca-certificates gnupg curl ssh -y
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] http://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg  add - && apt-get update -y && apt-get install google-cloud-cli -y

# Install docker to enable docker in docker functionality
RUN curl -fsSL https://get.docker.com -o get-docker.sh
RUN sh get-docker.sh

# Install wanna
ARG WANNA_VERSION
RUN pip install wanna-ml==$WANNA_VERSION

# Create wanna folder
WORKDIR /wanna

# Copy samples
COPY samples samples

ENV SHELL=/bin/bash

ENTRYPOINT ["/bin/bash"]