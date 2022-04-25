from typing import NamedTuple

from kfp.v2.dsl import Dataset, Output, component


@component(
    base_image="gcr.io/deeplearning-platform-release/tf-cpu.2-8",
    packages_to_install=["tensorflow", "tensorflow-io-gcs-filesystem", "tfx-bsl", "pyarrow", "tensorboard", "apache-beam", "keras-datasets"]
    # pip_index_url=[]
)
def data_prep_op(dataset_train: Output[Dataset], dataset_test: Output[Dataset], dataset_val: Output[Dataset]) -> NamedTuple("outputs",
                                                                                              [
                                                                                                  ("dataset_train_path", str),
                                                                                                  ("dataset_test_path", str),
                                                                                                  ("dataset_val_path", str)
                                                                                              ]):
    import tensorflow as tf
    import tensorflow_datasets as tfds
    from collections import namedtuple

    train_ds, test_ds = tfds.load('cifar10', split=['train', 'test']) # , as_supervised=True, batch_size=-1
    train_dataset = train_ds.take(4000)
    val_dataset = train_ds.skip(4000)
    test_dataset = test_ds.take(4000)

    train_dataset_path = dataset_train.path
    val_dataset_path = dataset_val.path
    test_dataset_path = dataset_test.path

    def serialize_example(image, label):
        feature = {
            # Normalize the image to range [0, 1].
            'image': tf.train.Feature(float_list=tf.train.FloatList(value=(image.numpy()/255.0).reshape(-1))),
            'label': tf.train.Feature(int64_list=tf.train.Int64List(value=[label]))
        }
        example = tf.train.Example(features=tf.train.Features(feature=feature))
        return example.SerializeToString()

    def dataset_generator(dataset):
        def gen():
            for features in dataset:
                del features['id']
                yield serialize_example(**features)
        return gen

    serialized_train_features_dataset = tf.data.Dataset.from_generator(
        dataset_generator(train_dataset), output_types=tf.string, output_shapes=()
    ).prefetch(tf.data.AUTOTUNE)

    writer = tf.data.experimental.TFRecordWriter(train_dataset_path)
    writer.write(serialized_train_features_dataset)

    serialized_val_features_dataset = tf.data.Dataset.from_generator(
        dataset_generator(val_dataset), output_types=tf.string, output_shapes=()
    ).prefetch(tf.data.AUTOTUNE)

    writer = tf.data.experimental.TFRecordWriter(val_dataset_path)
    writer.write(serialized_val_features_dataset)

    serialized_test_features_dataset = tf.data.Dataset.from_generator(
        dataset_generator(test_dataset), output_types=tf.string, output_shapes=()
    ).prefetch(tf.data.AUTOTUNE)

    writer = tf.data.experimental.TFRecordWriter(test_dataset_path)
    writer.write(serialized_test_features_dataset)

    outputs = namedtuple("outputs", ["dataset_train_path", "dataset_test_path", "dataset_val_path"])
    return outputs(
        dataset_train_path=train_dataset_path,
        dataset_test_path=test_dataset_path,
        dataset_val_path=val_dataset_path
    )
