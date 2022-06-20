---
title: WANNA Job
summary: How to use wanna job command
authors:
    - Joao Da Silva
    - Michal Mrázek
date: 2022-04-06
---

# WANNA Job

## Hyper-parameter tuning
A custom job can be simply converted to a hyper-parameter tuning job just by adding 
one extra parameter called `hp_tuning`. This will start a series of jobs (instead of just one job) 
and try to find the best combination of hyper-parameters in regard to a target variable that you specify.

Read [the official documentation](https://cloud.google.com/ai-platform/training/docs/using-hyperparameter-tuning) for more information.

In general, you have to set which hyper-parameters are changeable, which metric you want to optimize over
and how many trials you want to run. You also need to adjust your training script so it would accept
hyper-parameters as script arguments and report the optimized metric back to Vertex-Ai.

#### Setting hyper-parameter space
Your code should accept a script arguments with name matching `wanna.yaml` config.
For example, if you want to fine-tune the learning rate in your model:

In `wanna.yaml` config:

```
    hp_tuning:
      parameters:
        - var_name: learning_rate
          type: double
          min: 0.001
          max: 1
          scale: log
```

And the python script should accept the same argument with the same type:

```
  parser = argparse.ArgumentParser()
  parser.add_argument(
      '--learning_rate',
      required=True,
      type=float,
      help='learning rate')
```

Currently, you can use parameters of type `double`, `integer`, `discrete` and `categorical`.
Each of them must be specified by `var_name`, `type` and additionaly:

- `double`: `min`, `max` and `scale` (`linear` / `log`)
- `integer`: `min`, `max` and `scale` (`linear` / `log`)
- `discrete`: `values` (list of possible values)  and `scale` (`linear` / `log`)
- `categorical`: `values` (list of possible values)


#### Setting target metric
You can choose to either maximize or minimize your optimized metric. Example in `wanna.yaml`:

```
    hp_tuning:
      metrics: {'accuracy':'maximize'}
      parameters:
        ...
```

Your python script must report back the metric during training. In TensorFlow/Keras you can use
a callback to write the metric to the TensorFlow summary - [documentation](https://cloud.google.com/ai-platform/training/docs/using-hyperparameter-tuning#tensorflow_with_a_runtime_version).

In any other case, you should use [cloudml-hypertune](https://github.com/GoogleCloudPlatform/cloudml-hypertune) library.

```
import hypertune

hpt = hypertune.HyperTune()
hpt.report_hyperparameter_tuning_metric(
    hyperparameter_metric_tag='accuracy',
    metric_value=0.987,
    global_step=1000)
```

#### Setting number of trials and search algorithm
The number of trials can be influenced by `max_trial_count` and `parallel_trial_count`.

Search through hyper-parameter space can be `grid`, `random` or if not any of those two are set,
the default [Bayesian Optimization](https://cloud.google.com/blog/products/ai-machine-learning/hyperparameter-tuning-cloud-machine-learning-engine-using-bayesian-optimization) will be used.
