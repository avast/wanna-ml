# Python custom job packaging 

https://cloud.google.com/vertex-ai/docs/training/create-python-pre-built-container

`python setup.py sdist --formats=gztar`

`gsutil cp dist/trainer-0.1.tar.gz gs://wanna-ml/trainer-0.1.tar.gz`