import abc
import subprocess
from typing import Dict, List, Optional

import typer

from wanna.cli.gcloud.models import GCPConfig, ServiceAccount


class GCloudCommand(abc.ABC):
    def __init__(self, args: List[str], labels: Dict[str, str] = {}) -> None:
        self.args = args
        self.labels = labels

    def _prepare_labels(self) -> List[str]:
        if len(self.labels.items()) > 0:
            fmt = []

            for k, v in self.labels.items():
                fmt.append(f"{k}={v}")

            fmt = ",".join(fmt)
            return f"--labels={fmt}"
        else:
            return ""

    @property
    def command(self) -> List[str]:
        labels = self._prepare_labels()
        cmd = ["gcloud"] + self.args + [labels]
        clean_cmd = list(filter(lambda x: x != "", cmd))
        typer.echo(f"executing {clean_cmd}")
        return clean_cmd

    def run(self):
        #  --format json
        gcloud_call = subprocess.Popen(
            self.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        output, errors = gcloud_call.communicate()
        gcloud_call.wait()

        if gcloud_call.returncode != 0:
            typer.echo(errors)
            raise typer.Exit(code=gcloud_call.returncode)
        else:
            typer.echo(errors)
            typer.echo(output)


class GCloudService(abc.ABC):
    def __init__(self, gcp_config: Optional[GCPConfig]) -> None:
        if gcp_config.service_account:
            self._init_service_account(gcp_config.service_account)

        if len(gcp_config.settings) > 0:
            for k, v in gcp_config.settings.items():
                self.set_config(k, v).run()

    def set_config(self, key: str, value: str) -> GCloudCommand:
        #   gcloud auth activate-service-account --key-file=${GOOGLE_APPLICATION_CREDENTIAL}
        return GCloudCommand(["config", "set", key, value])

    def _init_service_account(self, service_account: ServiceAccount) -> None:
        # gcloud auth activate-service-account
        return GCloudCommand(
            [
                "auth",
                "activate-service-account",
                service_account.account_email,
                "--key-file",
                service_account.account_json,
            ]
        ).run()


class VertexAIService(GCloudService):
    def __init__(self, gcp_config: Optional[GCPConfig]) -> None:
        super(VertexAIService, self).__init__(gcp_config)

    def create_job(self):
        pass

    def delete_job(self):
        pass
