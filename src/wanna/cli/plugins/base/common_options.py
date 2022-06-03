import typer

from wanna.cli.deployment.models import PushMode

profile_name_option = typer.Option(
    "default",
    "--profile",
    "-p",
    envvar="WANNA_GCP_PROFILE_NAME",
    help="Name of the GCP profile you want to use. "
    "Profiles are loaded from wanna-ml yaml config and "
    "(optionally) from WANNA_GCP_PROFILE_PATH",
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

docker_registry_option = typer.Option(
    None,
    "--registry",
    "-r",
    envvar="WANNA_DOCKER_REGISTRY",
    help="override docker registry and takes precedence over"
    "wanna.yaml and fallback registries"
    "(optionally) from WANNA_DOCKER_REGISTRY",
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
