FROM docker.ida.avast.com/dockerhub/python:3.8-buster

# Avast related settings
RUN sed -r 's%http://deb.debian.org/debian%http://apt.ida.avast.com/artifactory/apt.deb.debian.org%g' -i /etc/apt/sources.list
RUN sed -r 's%http://security.debian.org/debian-security%http://apt.ida.avast.com/artifactory/apt.security.debian.org%g' -i /etc/apt/sources.list

ENV PIP_DISABLE_PIP_VERSION_CHECK=on
ENV PIP_CONFIG_FILE $HOME/.pip/pip.conf
ARG INDEX_URL=https://artifactory.ida.avast.com/artifactory/api/pypi/pypi-remote/simple/
ARG EXTRA_INDEX_URL=https://artifactory.ida.avast.com/artifactory/api/pypi/pypi-local/simple/

RUN mkdir -p $HOME/.pip
RUN printf "[global]\nindex-url=$INDEX_URL\nextra-index-url=$EXTRA_INDEX_URL" > $HOME/.pip/pip.conf

RUN apt-get update -y \
    && apt-get install git docker \
    && apt-get clean

RUN pip install poetry pandas

RUN pip install --upgrade wanna

# Credentials entrypoint
COPY bin/entrypoint.sh /entrypoint.sh
RUN mkdir -p /credentials

ENV GOOGLE_APPLICATION_CREDENTIALS="/credentials/service_account.json"

RUN mkdir /wanna

WORKDIR /wanna

ENTRYPOINT ["/entrypoint.sh"]