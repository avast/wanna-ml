from typing import Optional

import typer

from wanna.core.deployment.models import PushMode

profile_name_option = typer.Option(
    "default",
    "--profile",
    "-p",
    envvar="WANNA_GCP_PROFILE_NAME",
    help="Name of the GCP profile you want to use. "
    "Profiles are loaded from wanna-ml yaml config and "
    "(optionally) from this file too.",
)

wanna_file_option = typer.Option(
    "wanna.yaml",
    "--file",
    "-f",
    envvar="WANNA_FILE",
    help="Path to the wanna-ml yaml configuration",
)

push_mode_option: PushMode = typer.Option(
    PushMode.all,
    "--mode",
    "-m",
    help="Push mode, this is useful if you want to "
    "push containers in one step and deploy instances in other."
    "Use all for dev",
)


def instance_name_option(
    instance_type: str, operation: str, help: Optional[str] = None
):
    return typer.Option(
        "all",
        "--name",
        "-n",
        help=help
        or f"Specify only one {instance_type} from your wanna-ml yaml configuration to {operation}. "
        f"Choose 'all' to {operation} all {instance_type}s.",
    )


def version_option(instance_type: str):
    return typer.Option("dev", "--version", "-v", help=f"{instance_type} version")
