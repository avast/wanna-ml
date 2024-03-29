---
title: WANNA managed-notebook
summary: How to use wanna managed-notebook command
authors:
  - Jacek Hebda
  - Joao Da Silva
  - Michal Mrázek
date: 2022-06-03
---
  
# WANNA Managed notebook
It offers a simple way of deploying Jupyter Notebooks on GCP, with minimum environment
set up, automatic mount of all GCS buckets in the project, connection do Dataproc clusters and more.

::: wanna.core.models.notebook.ManagedNotebookModel
    :docstring:

### Dataproc clusters and metastore
If you want to run Spark jobs on a Dataproc cluster and also have a Hive Metastore service available
as your default Spark SQL engine:

- Create a Dataproc Metastore in your GCP project & region in the Google Cloud UI
- Create a Dataproc cluster connected to this metastore, with a subnet specified. e.g.:
```
gcloud dataproc clusters create cluster-test --enable-component-gateway --region europe-west1 --subnet cloud-lab --zone europe-west1-b --single-node --optional-components JUPYTER --dataproc-metastore projects/cloud-lab-304213/locations/europe-west1/services/jacek-test
```
- Run your managed notebook. As kernel use Pyspark on the remote Dataproc cluster that you have just created
- Test your spark Session for access. This example creates a database in your metastore:
```
spark = SparkSession \
    .builder \
    .appName("MetastoreTest") \
    .getOrCreate()

query = """CREATE DATABASE testdb"""
spark.sql(query)
```    

### Tensorboard integration
`tb-gcp-uploader` is needed to upload the logs to the tensorboard instance. A detailed
tutorial on this tool can be found [here](https://cloud.google.com/vertex-ai/docs/experiments/tensorboard-overview).

If you set the `tensorboard_ref` in the WANNA yaml config, we will export the tensorboard resource name
as `AIP_TENSORBOARD_LOG_DIR`.

### Example
```
managed-notebooks:
  - name: example
    owner: jacek.hebda@avast.com
    machine_type: n1-standard-1
    labels:
      notebook_usecase: wanna-notebook-sample
    tags:
    metadata:
    gpu:
      count: 1
      accelerator_type: NVIDIA_TESLA_T4
    data_disk:
      disk_type: pd_standard
      size_gb: 100
    tensorboard_ref:
    kernels:
    network:
    subnet: 
    idle_shutdown: True
    idle_shutdown_timeout: 180
```
