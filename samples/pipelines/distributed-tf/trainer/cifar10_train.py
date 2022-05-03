import argparse
import os

import tensorflow as tf
from tensorflow.keras import layers, models, losses

def create_model():
    print(f"creating model")
    model = models.Sequential([
        layers.Conv2D(32, (3, 3), activation='relu', input_shape=(32, 32, 3)),
        layers.MaxPooling2D(2, 2),
        layers.Conv2D(64, (3, 3), activation='relu'),
        layers.MaxPooling2D(2, 2),
        layers.Conv2D(64, (3, 3), activation='relu'),
        layers.Flatten(),
        layers.Dense(64, activation='relu'),
        layers.Dense(10, activation='softmax')
    ])
    print(f"compiling model")
    model.compile(optimier='adam', loss=losses.SparseCategoricalCrossentropy(), metrics=['accuracy'])
    return model


def extract(example):
    data = tf.io.parse_example(
        example,
        # Schema of the example.
        {
            'image': tf.io.FixedLenFeature(shape=(32, 32, 3), dtype=tf.float32),
            'label': tf.io.FixedLenFeature(shape=(), dtype=tf.int64)
        }
    )
    return data['image'], data['label']


def get_dataset(dataset_path):
    return (
        tf.data.TFRecordDataset([dataset_path])
            .map(extract, num_parallel_calls=tf.data.experimental.AUTOTUNE)
            .shuffle(1024)
            .batch(128)
            .cache()
            .prefetch(tf.data.experimental.AUTOTUNE)
    )


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('--epochs', dest='epochs', type=float, default=5.0)
    parser.add_argument('--train_dataset_path', type=str, required=True)
    parser.add_argument('--val_dataset_path', type=str, required=True)
    parser.add_argument('--test_dataset_path', type=str, required=True)

    args = parser.parse_args()

    epochs = int(args.epochs)
    train_dataset_path = args.train_dataset_path
    val_dataset_path = args.val_dataset_path
    test_dataset_path = args.test_dataset_path

    # Prep Datasets
    train_dataset = get_dataset(train_dataset_path)
    val_dataset = get_dataset(val_dataset_path)
    test_dataset = get_dataset(test_dataset_path)

    for k,v in os.environ.items():
        print(k, v)

    GCS_PATH_FOR_CHECKPOINTS = os.environ.get("AIP_CHECKPOINT_DIR")
    GCS_PATH_FOR_SAVED_MODEL = os.environ.get("AIP_MODEL_DIR")
    GCS_TENSORBOARD_LOG_DIR = os.environ.get("AIP_TENSORBOARD_LOG_DIR")

    # A distributed strategy to take advantage of available hardware.
    # No-op otherwise.
    multi_worker_mirrored_strategy = tf.distribute.MirroredStrategy()
    with multi_worker_mirrored_strategy.scope():


        model = create_model()




    # Restore from the latest checkpoint if available.
    print(f"checkpoint checkking in {GCS_PATH_FOR_CHECKPOINTS}")
    latest_ckpt = tf.train.latest_checkpoint(GCS_PATH_FOR_CHECKPOINTS)
    if latest_ckpt:
        print("Loading weights from last checkpoint")
        model.load_weights(latest_ckpt)

    # Create a callback to store a check at the end of each epoch.
    ckpt_callback = tf.keras.callbacks.ModelCheckpoint(
        filepath=GCS_PATH_FOR_CHECKPOINTS,
        monitor='val_loss',
        save_weights_only=True
    )

    print(f"Setting tensorboard callback to {GCS_TENSORBOARD_LOG_DIR}")
    tensorboard_callback = tf.keras.callbacks.TensorBoard(
        log_dir=GCS_TENSORBOARD_LOG_DIR,
        histogram_freq=1
    )

    print(f"fitting model")
    model.fit(train_dataset, epochs=epochs, validation_data=val_dataset, callbacks=[ckpt_callback, tensorboard_callback], batch_size=128)

    print(f"evaluating model")
    model.evaluate(test_dataset, verbose=2)

    # Export the model to GCS.
    print(f"Saving model to {GCS_PATH_FOR_SAVED_MODEL}")
    model.save(GCS_PATH_FOR_SAVED_MODEL)


if __name__ == "__main__":
    main()
