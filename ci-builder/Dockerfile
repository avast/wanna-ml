FROM docker-luft.ida.avast.com/avast/bds/mlops/miniconda3:4.8.2.6

RUN apt-get update -y \
    && apt-get install git \
    && apt-get clean

ENV CONDARC /opt/conda/config/.condarc
RUN conda update conda pip \
    && pip install packaging poetry \
    && pip install --upgrade wanna
