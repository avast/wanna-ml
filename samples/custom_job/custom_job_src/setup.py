from setuptools import find_packages, setup

REQUIRED_PACKAGES = ["tensorflow_datasets==1.3.0"]

setup(
    name="trainer",
    version="0.1",
    install_requires=REQUIRED_PACKAGES,
    packages=find_packages(),
    include_package_data=True,
    description="My training application.",
)
