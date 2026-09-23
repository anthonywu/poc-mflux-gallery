"""Configuration shared by the CLI and application factory."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class AppConfig:
    directory: Path
    host: str = "127.0.0.1"
    port: int = 9000
    delete_mode: Literal["trash", "permanent"] = "permanent"
    load_limit: int = 100
    debug: bool = False
    resize_max_width: int = 512

    def __post_init__(self) -> None:
        directory = Path(self.directory).resolve()
        if not directory.exists():
            raise FileNotFoundError(f"Directory '{directory}' does not exist.")
        if not directory.is_dir():
            raise NotADirectoryError(f"'{directory}' is not a directory.")
        object.__setattr__(self, "directory", directory)
