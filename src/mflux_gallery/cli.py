import argparse
from pathlib import Path


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="genai-gallery", description="Manage an AI image gallery."
    )

    parser.add_argument(
        "directory",
        type=Path,
        help="The directory containing the images for the gallery",
    )

    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="The host address to run the gallery server on (default: 127.0.0.1)",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=9000,
        help="The port number to run the gallery server on (default: 9000)",
    )

    parser.add_argument(
        "--delete-mode",
        "-d",
        choices=["trash", "permanent"],
        default="permanent",
        help="Specify the delete mode for images (default: permanent)",
    )

    parser.add_argument(
        "--load-limit",
        "-l",
        type=int,
        default=100,
        help="Specify the maximum number of images to load (default: 100)",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        default=False,
        help="Specify the debug mode - more verbose and instant reload.",
    )

    parser.add_argument(
        "--resize-max-width",
        "-w",
        type=int,
        default=512,
        help="Specify the maximum width for image resizing (default: 512)",
    )

    return parser
