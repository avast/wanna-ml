from typing import NamedTuple

from kfp.v2.dsl import (Dataset,
                        Input,
                        Model,
                        Output,
                        Metrics,
                        ClassificationMetrics,
                        component)


@component(
    base_image="python:3.9",
    packages_to_install=[
        "pandas",
        "sklearn",
        "xgboost"
    ],
)
def eval_model_op(
        test_set: Input[Dataset],
        xgb_model: Input[Model],
        metrics: Output[ClassificationMetrics],
        smetrics: Output[Metrics]
) -> NamedTuple("Outputs", [("test_score", float)]):
    from xgboost import XGBClassifier
    import pandas as pd
    from collections import namedtuple

    data = pd.read_csv(test_set.path)
    model = XGBClassifier()
    model.load_model(xgb_model.path)

    score = model.score(
        data.drop(columns=["target"]),
        data.target,
    )

    from sklearn.metrics import roc_curve
    y_scores = model.predict_proba(data.drop(columns=["target"]))[:, 1]
    fpr, tpr, thresholds = roc_curve(
        y_true=data.target.to_numpy(), y_score=y_scores, pos_label=True
    )
    metrics.log_roc_curve(fpr.tolist(), tpr.tolist(), thresholds.tolist())

    from sklearn.metrics import confusion_matrix
    y_pred = model.predict(data.drop(columns=["target"]))

    metrics.log_confusion_matrix(
        ["False", "True"],
        confusion_matrix(
            data.target, y_pred
        ).tolist(),  # .tolist() to convert np array to list.
    )

    test_score = float(score)
    xgb_model.metadata["test_score"] = test_score
    smetrics.log_metric("score", test_score)
    outputs = namedtuple("Outputs", ["test_score"])
    return outputs(test_score)
