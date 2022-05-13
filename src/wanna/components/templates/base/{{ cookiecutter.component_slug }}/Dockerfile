# TODO: Add Artifactory IDA repos for in Landing Zone

FROM gcr.io/deeplearning-platform-release/{{cookiecutter.component_framework}}:latest as env_builder

WORKDIR /build

RUN conda create -y -n {{cookiecutter.component_slug}} python=3.8

RUN eval "$(conda shell.bash hook)" \
    && conda activate {{cookiecutter.component_slug}} \
    && pip install conda-pack \
    && conda pack -o /build/env.tar.gz \
    && mkdir /venv && cd /venv && tar xf /build/env.tar.gz \
    && rm /build/env.tar.gz

# We've put venv in same path it'll be in final image,
# so now fix up paths:
RUN /venv/bin/conda-unpack

FROM gcr.io/deeplearning-platform-release/{{cookiecutter.component_framework}}:latest

WORKDIR /

# Copy /venv from the previous stage
COPY --from=env_builder /venv /venv

# ENV PATH="${DL_ANACONDA_HOME}/envs/train/venv/bin:$PATH"

ENV PATH="/venv/bin:$PATH"

# Copies the data code to the docker image.
COPY . /{{cookiecutter.component_slug}}

RUN pip install /{{cookiecutter.component_slug}}
