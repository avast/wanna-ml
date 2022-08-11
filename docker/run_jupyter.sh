#!/bin/bash

pip install jupyterlab

PORT=${1:-8888}

jupyter lab --ip 0.0.0.0 --port $PORT --no-browser --allow-root