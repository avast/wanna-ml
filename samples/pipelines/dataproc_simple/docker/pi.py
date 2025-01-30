#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from datetime import date, datetime
from pathlib import Path
from typing import Union

import click
from pyspark.sql import Row, SparkSession


def kubeflow_output_dump(path: Union[Path, str], content: str):
    print(f"dumping output values to {path}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def maybe_replace_gcs(path: str):
    if path.startswith("/gcs/"):
        return path.replace("/gcs/", "gs://")
    else:
        return path


@click.command()
@click.option(
    "--data_output",
    envvar="DATA_OUTPUT",
    required=True,
)
def main(data_output):
    spark = SparkSession.builder.appName("PythonPi").getOrCreate()

    df = spark.createDataFrame(
        [
            Row(
                a=1, b=4.0, c="GFG1", d=date(2000, 8, 1), e=datetime(2000, 8, 1, 12, 0)
            ),
            Row(
                a=2, b=8.0, c="GFG2", d=date(2000, 6, 2), e=datetime(2000, 6, 2, 12, 0)
            ),
            Row(
                a=4, b=5.0, c="GFG3", d=date(2000, 5, 3), e=datetime(2000, 5, 3, 12, 0)
            ),
        ]
    )

    # show table
    df.show()

    # show schema
    df.printSchema()

    p = "/tmp/data.csv"
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    print(f"Going to save data to: {p}")
    df.coalesce(1).write.option("header", "true").option("sep", ",").mode(
        "overwrite"
    ).csv(p)

    kubeflow_output_dump(f"{data_output}", str(p))


if __name__ == "__main__":
    main()
