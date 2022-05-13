import typer

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


def instance_name_option(instance_type: str, operation: str, help: str = None):
    return typer.Option(
        "all",
        "--name",
        "-n",
        help=help
        or f"Specify only one {instance_type} from your wanna-ml yaml configuration to {operation}. "
        f"Choose 'all' to {operation} all {instance_type}s.",
    )
