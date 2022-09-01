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
    "wanna.yaml", "--file", "-f", envvar="WANNA_FILE", help="Path to the wanna-ml yaml configuration"
)

push_mode_option: PushMode = typer.Option(
    PushMode.all,
    "--mode",
    "-m",
    help="Pipeline push mode, due to CI/CD not "
    "allowing to push to docker registry from "
    "GCP Agent, we need to split it. "
    "Use all for dev",
)

skip_containers_option = typer.Option(
    False,
    "--skip-containers",
    help="Skip container building and pushing. "
    "This assumes that the container is already prepared in Artifact Registry.",
)


def instance_name_option(instance_type: str, operation: str, help: str = None):
    return typer.Option(
        "all",
        "--name",
        "-n",
        help=help
        or f"Specify only one {instance_type} from your wanna-ml yaml configuration to {operation}. "
        f"Choose 'all' to {operation} all {instance_type}s.",
    )
