import argparse
import os
from collections import namedtuple

import numpy as np
import pandas as pd
from sklearn import metrics
from tensorboardX import SummaryWriter
from xgboost import XGBClassifier


def get_args():
    """Define the task arguments with the default values.
    Returns:
        experiment parameters
    """
    args_parser = argparse.ArgumentParser()

    # Saved model arguments
    args_parser.add_argument("--model-dir", default=os.getenv("AIP_MODEL_DIR"), help="GCS location to export models")
    args_parser.add_argument("--model-name", default="wanna-sklearn-sample", help="The name of your saved model")

    return args_parser.parse_args()


def main():
    """Setup / Start the experiment"""
    args = get_args()
    print(args)
    model_dir = args.model_dir
    model_name = args.model_name
    writer = SummaryWriter(log_dir=os.environ["AIP_TENSORBOARD_LOG_DIR"])

    def accuracy(preds, train_data):
        preds = 1.0 / (1.0 + np.exp(-preds))
        return "accuracy", np.mean(train_data[preds > 0.5]), True

    def TensorBoardXGBCallback():
        def callback(env):
            for name, val in env.evaluation_result_list:
                writer.add_scalar(name, val, env.iteration)

        return callback

    def get_scores(y_true, y_pred):
        scores = {}
        scores["accuracy"] = metrics.accuracy_score(y_true, y_pred)
        scores["precision"] = metrics.precision_score(y_true, y_pred)
        scores["recall"] = metrics.recall_score(y_true, y_pred)
        scores["f1"] = metrics.f1_score(y_true, y_pred)
        return scores

    data = pd.read_csv(os.environ["DATA_DIR"])

    model = XGBClassifier(objective="binary:logistic")

    X_train, X_val = data.drop(columns=["target"]), data.target

    model.fit(
        data.drop(columns=["target"]),
        data.target,
        verbose=True,
        callbacks=[TensorBoardXGBCallback()],
        eval_metric=["logloss"],
    )

    y_predict_train = model.predict(X_train)
    y_predict_val = model.predict(X_val)

    score = model.score(
        data.drop(columns=["target"]),
        data.target,
    )

    for key, val in get_scores(y_train, y_predict_train).items():
        writer.add_text(f"train_{key}", str(val))

    for key, val in get_scores(y_val, y_predict_val).items():
        writer.add_text(f"val_{key}", str(val))

    # model_artifact.metadata["framework"] = "XGBOOST"
    # model_artifact.metadata["train_score"] = float(score)
    model_path = f"{model_dir}/model.bst"

    model.save_model(model_path)

    # set output variables
    outputs = namedtuple("Outputs", ["train_score", "model_artifact_path"])
    # model_path = str(model_artifact.path).replace("/gcs/", "gs://").replace("model.bst", "")
    return outputs(
        float(score),
        model_path,
    )


if __name__ == "__main__":
    main()
