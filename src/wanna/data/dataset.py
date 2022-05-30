# Docs
# https://cloud.google.com/python/docs/reference/dataplex/latest
# https://cloud.google.com/python/docs/reference/datacatalog/latest
# PIP
# pip install google-cloud-dataplex google-cloud-datacatalog

from typing import Union, List, Optional

from google.cloud import bigquery
from google.cloud import dataplex_v1
from google.cloud.datacatalog_v1 import DataCatalogClient
from google.cloud.dataplex_v1 import DataplexServiceClient
from pydantic import BaseModel


class Dataset(BaseModel):
    name: str


class BigQueryDataset(Dataset):
    name: str

    def get_dataset_path(self) -> str:
        resource = self.name.split("/")
        project = resource[1]
        dataset_id = resource[-1]
        return f"{project}.{dataset_id}"

    def get_dataset_table(self, table_name) -> Optional[str]:
        client = bigquery.Client()
        tables = client.list_tables(self.get_dataset_path())
        table = list(filter(lambda t: t.table_id == table_name, tables))
        if table:
            return table[0].table_id
        else:
            return None


class GCSDataset(Dataset):
    name: str

    def get_bucket(self) -> str:
        bucket_name = self.name.split("/")[-1]
        return bucket_name


"""
US Burger gcp project we have current setup:

Lake -> Zone(Raw Zone, Curated Zone) -> Assets(GCP, BigQuery resource names)

CTO DATALAKE - Lake
    CTO DATALAKE NO PII -> Curated Zone(empty now)
    CTO RAW ZONE -> Raw Zone
        hotdog-agentx-data-asset
        malware-training-sets-test
"""


class WannaDatasetCatalogItem(BaseModel):
    zone_id: str
    lake_id: str
    asset_id: str


class WannaDataset(BaseModel):
    name: str
    metadata: WannaDatasetCatalogItem


class WannaData(BaseModel):
    catalog: List[WannaDataset]


class DatasetService:

    def __init__(self, wanna_catalog: List[WannaDataset]) -> None:
        self.data_catalog = DataCatalogClient()
        self.data_plex = DataplexServiceClient()
        self.asset_catalog = {
            dataset.name: dataset.metadata for dataset in wanna_catalog
        }

    def _get_wanna_dataset(self, spec) -> Union[GCSDataset, BigQueryDataset]:
        # using str as had some import issues, just mucking about
        if spec.type_.name == "STORAGE_BUCKET":
            return GCSDataset(name=spec.name)
        elif spec.type_.name == "BIGQUERY_DATASET":
            return BigQueryDataset(name=spec.name)
        else:
            raise ValueError(f"{spec.type_.name} is unknown to WANNA Data lib")

    def get_dataset(self, name: str) -> Dataset:
        dataset = self.asset_catalog.get(name)

        if dataset:
            request = dataplex_v1.GetAssetRequest({
                "name": f"projects/us-burger-gcp-poc/locations/europe-west1/lakes/{dataset.lake_id}"
                        f"/zones/{dataset.zone_id}/assets/{dataset.asset_id}",
            })

            response = self.data_plex.get_asset(request=request)
            return self._get_wanna_dataset(response.resource_spec)
        else:
            raise ValueError(f"dataset {name} is not part of wanna ml data catalog")

    def create_dataset(self) -> Dataset:
        pass


if __name__ == "__main__":
    wanna_catalog = [
        WannaDataset(
            name="raw-agentx-dataset",
            metadata=WannaDatasetCatalogItem(
                lake_id="cto-datalake-test",
                zone_id="cto-datalake-raw-zone-test",
                asset_id="hotdog-agentx-data-asset"
            )
        ),
        WannaDataset(
            name="cto-bigquery-test",
            metadata=WannaDatasetCatalogItem(
                lake_id="cto-datalake-test",
                zone_id="cto-datalake-raw-zone-test",
                asset_id="cto-bigquery-test"
            )
        )

    ]
    dataset_service = DatasetService(wanna_catalog)

    bq_dataset = dataset_service.get_dataset("cto-bigquery-test")
    print(bq_dataset.get_dataset_path())
    print(bq_dataset.get_dataset_table("wanna-data-test"))

    gcs_dataset = dataset_service.get_dataset("raw-agentx-dataset")
    print(gcs_dataset.get_bucket())



