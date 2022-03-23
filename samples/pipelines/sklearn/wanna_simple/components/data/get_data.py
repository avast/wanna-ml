from collections import namedtuple

from kfp.v2.dsl import Dataset, Output, component

GetDataOutputs = namedtuple("GetDataOutputs", ["dataset_train_path", "dataset_test_path"])


@component(
    base_image="python:3.9",
    packages_to_install=["pandas", "sklearn"],
)
def get_data_op(dataset_train: Output[Dataset], dataset_test: Output[Dataset]) -> GetDataOutputs:
    import pandas as pd
    from sklearn import datasets
    from sklearn.model_selection import train_test_split as tts

    # import some data to play with
    data_raw = datasets.load_breast_cancer()
    data = pd.DataFrame(data_raw.data, columns=data_raw.feature_names)
    data["target"] = data_raw.target

    train, test = tts(data, test_size=0.3)

    train.to_csv(dataset_train.path)
    test.to_csv(dataset_test.path)

    return GetDataOutputs(dataset_train_path=dataset_train.path, dataset_test_path=dataset_test.path)
