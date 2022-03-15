import os

from setuptools import find_packages
from setuptools import setup

REQUIRED_PACKAGES = [
    'transformers',
    'datasets',
    'tqdm',
    'cloudml-hypertune',
    "pandas",
    "sklearn",
    "xgboost"
    #  'wanna-core'
]

version = os.environ.get('WANNA_PROJECT_VERSION', 'dev0')

setup(
    name='wanna-sklearn-sample-trainer',
    version=version,
    install_requires=REQUIRED_PACKAGES,
    packages=find_packages(),
    include_package_data=True,
    description='Vertex AI | Training | sklearn | Python Package'
)
