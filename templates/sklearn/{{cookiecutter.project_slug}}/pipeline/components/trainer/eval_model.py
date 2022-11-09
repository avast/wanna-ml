from typing import NamedTuple

from kfp.v2.dsl import ClassificationMetrics, Dataset, Input, Metrics, Model, Output, component


@component(
    base_image="python:3.9",
    packages_to_install=["pandas", "sklearn", "xgboost"],
)
def eval_model_op(
    test_set: Input[Dataset], xgb_model: Input[Model], metrics: Output[ClassificationMetrics], smetrics: Output[Metrics]
) -> NamedTuple("outputs", [("test_score", float),]):
    from collections import namedtuple

    import pandas as pd
    from sklearn.metrics import confusion_matrix, roc_curve
    from xgboost import XGBClassifier

    test_set = pd.read_csv(test_set.path)
    model = XGBClassifier()
    model.load_model(xgb_model.path)

    X_test, y_test = test_set.drop(columns=["target"]), test_set.target

    score = model.score(X_test, y_test)

    y_scores = model.predict_proba(X_test)[:, 1]

    fpr, tpr, thresholds = roc_curve(y_true=y_test.to_numpy(), y_score=y_scores, pos_label=True)
    metrics.log_roc_curve(fpr.tolist(), tpr.tolist(), thresholds.tolist())

    y_pred = model.predict(X_test)
    metrics.log_confusion_matrix(
        ["False", "True"],
        confusion_matrix(y_test, y_pred).tolist(),  # .tolist() to convert np array to list.
    )

    test_score = float(score)
    xgb_model.metadata["test_score"] = test_score
    smetrics.log_metric("score", test_score)
    outputs = namedtuple("outputs", ["test_score"])
    return outputs(test_score=test_score)
