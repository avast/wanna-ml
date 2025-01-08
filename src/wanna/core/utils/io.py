import os
import tarfile
from pathlib import Path

import igittigitt


def tar_docker_context(source_dir: Path, target_tar_file: Path, ignore_patterns: list[str] = []):
    """
    Tars a directory recursively while optionally skipping files based on ignore patterns.

    :param source_dir: Path to the directory to be tarred.
    :param target_tar_file: Path to the output TAR file.
    :param ignore_patterns: List of file patterns to skip (e.g., ['*.pyc', '*.log']).
    """

    parser = igittigitt.IgnoreParser()
    for pattern in ignore_patterns:
        parser.add_rule(pattern, source_dir)

    os.makedirs(target_tar_file.parent.absolute(), exist_ok=True)
    with tarfile.open(target_tar_file, "w:gz") as the_tar_file:
        for root, _, files in os.walk(source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                if parser.match(file_path):
                    continue
                the_tar_file.add(file_path, arcname=os.path.relpath(file_path, source_dir))
