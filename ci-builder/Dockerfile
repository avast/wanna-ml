FROM docker-luft.ida.avast.com/dockerhub/google/cloud-sdk:359.0.0-slim

# Avast related settings
RUN sed -r 's%http://deb.debian.org/debian%http://apt.ida.avast.com/artifactory/apt.deb.debian.org%g' -i /etc/apt/sources.list
RUN sed -r 's%http://security.debian.org/debian-security%http://apt.ida.avast.com/artifactory/apt.security.debian.org%g' -i /etc/apt/sources.list

ENV PIP_DISABLE_PIP_VERSION_CHECK=on
ENV PIP_CONFIG_FILE $HOME/.pip/pip.conf
ARG INDEX_URL=https://artifactory.ida.avast.com/artifactory/api/pypi/pypi-remote/simple/
ARG EXTRA_INDEX_URL=https://artifactory.ida.avast.com/artifactory/api/pypi/pypi-local/simple/

RUN mkdir -p $HOME/.pip
RUN printf "[global]\nindex-url=$INDEX_URL\nextra-index-url=$EXTRA_INDEX_URL" > $HOME/.pip/pip.conf

RUN apt-get update -y && \
    && apt-get remove -y docker docker-engine docker.io \
    && && apt-get install -y git docker.io wget

# Conda Environment
ENV MINICONDA_VERSION py38_4.9.2
ENV PATH /opt/miniconda/bin:$PATH
RUN wget -qO /tmp/miniconda.sh https://artifactory.ida.avast.com/artifactory/packagesfromnet-generic-local/temp/miniconda/Miniconda3-${MINICONDA_VERSION}-Linux-x86_64.sh && \
    bash /tmp/miniconda.sh -bf -p /opt/miniconda && \
    conda clean -ay && \
    rm -rf /opt/miniconda/pkgs && \
    rm /tmp/miniconda.sh

COPY config/.condarc /opt/miniconda/config/.condarc
ENV CONDARC /opt/miniconda/config/.condarc

RUN conda create -n ci-builder python=3.8

RUN eval "$(conda shell.bash hook)" \
    && conda activate ci-builder \
    && pip install --upgrade wanna-ml

# Credentials entrypoint
COPY bin/entrypoint.sh /entrypoint.sh

WORKDIR /wanna

ENV PATH="/opt/miniconda/envs/ci-builder/bin:${PATH}"

ENTRYPOINT ["/entrypoint.sh"]
