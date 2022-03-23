from collections import namedtuple

from kfp.v2.dsl import Dataset, Input, Model, Output, component

TrainOutputs = namedtuple("TrainOutputs", ["train_score", "model_artifact_path"])


@component(
    base_image="python:3.9",
    packages_to_install=[
        "pandas",
        "sklearn",
        "xgboost",
    ],
)
def train_xgb_model_op(dataset: Input[Dataset], model_artifact: Output[Model]) -> TrainOutputs:

    import pandas as pd
    from xgboost import XGBClassifier

    data = pd.read_csv(dataset.path)

    model = XGBClassifier(objective="binary:logistic")

    model.fit(
        data.drop(columns=["target"]),
        data.target,
    )

    score = model.score(
        data.drop(columns=["target"]),
        data.target,
    )

    model_artifact.metadata["train_score"] = float(score)
    model_artifact.metadata["framework"] = "XGBOOST"
    # Vertex AI default serving expects model file to be called model.bst
    model_path = f"""{model_artifact.path.replace("model_artifact", "model.bst")}"""
    model_artifact.path = model_path
    model.save_model(model_artifact.path)

    # After save make model
    model_path = str(model_artifact.path).replace("/gcs/", "gs://").replace("model.bst", "")

    return TrainOutputs(
        train_score=float(score),
        model_artifact_path=model_path,
    )
