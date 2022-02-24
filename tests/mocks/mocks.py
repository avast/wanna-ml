from google.cloud.compute_v1.types import Image, ImageList
from google.cloud.compute_v1.types.compute import (
    MachineType,
    MachineTypeList,
    Zone,
    ZoneList,
    Region,
    RegionList,
)


class MockZonesClient:
    def list(self, project):
        zone_names = ["europe-west4-a", "us-east1-a"]
        return ZoneList(items=[Zone({"name": name}) for name in zone_names])


class MockRegionsClient:
    def list(self, project):
        region_names = ["europe-west1", "us-east1"]
        return RegionList(items=[Region({"name": name}) for name in region_names])


class MockImagesClient:
    def list(self, list_images_request):
        image_families = [
            "tf2-ent-2-5-cu110-notebooks",
            "tf2-ent-2-5-cu110-notebooks-debian-10",
            "tf-ent-2-3-cpu-ubuntu-2004",
            "tf-ent-2-3-cu110-notebooks-ubuntu-1804",
            "tf-ent-2-3-cu110-notebooks",
        ]
        return ImageList(items=[Image({"family": family}) for family in image_families])


class MockMachineTypesClient:
    def list(self, project, zone):
        print("ahoj")
        machine_type_names = [
            "n1-ultramem-160",
            "n2-highmem-96",
            "n2-standard-128",
            "n2d-standard-2",
        ]
        return MachineTypeList(
            items=[MachineType({"name": mtype}) for mtype in machine_type_names]
        )
