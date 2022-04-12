import typer

profile_option = typer.Option(
    "default",
    "--profile",
    "-p",
    envvar="WANNA_GCP_PROFILE_NAME",
    help="Name of the GCP profile you want to use. "
    "Profiles are loaded from wanna-ml yaml config and "
    "(optionally) from WANNA_GCP_PROFILE_PATH",
)

wanna_file_option = typer.Option("wanna.yaml", "--file", "-f", help="Path to the wanna-ml yaml configuration")


def instance_name_option(instance_type: str, operation: str):
    return typer.Option(
        "all",
        "--name",
        "-n",
        help=f"Specify only one {instance_type} from your wanna-ml yaml configuration to {operation}. "
        f"Choose 'all' to {operation} all {instance_type}s.",
    )
