#!/bin/bash

sudo su -c "mkdir -p /home/jupyter/mounted/gcs/" -s /bin/sh jupyter
sudo su -c "gcsfuse --implicit-dirs us-burger-gcp-poc-mooncloud /home/jupyter/mounted/gcs/" -s /bin/sh jupyter

