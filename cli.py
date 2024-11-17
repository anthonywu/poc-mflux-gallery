import argparse
from pathlib import Path


def create_parser():
    parser = argparse.ArgumentParser(
        prog="genai-gallery", description="Manage an AI image gallery."
    )

    # Positional argument for the directory
    parser.add_argument(
        "directory",
        type=Path,
        help="The directory containing the images for the gallery",
    )

    # Optional argument for the host
    parser.add_argument(
        "--host",
        type=str,
        required=False,
        default="0.0.0.0",
        help="The port number to run the gallery server on (default: 0.0.0.0)",
    )

    # Optional argument for the port
    parser.add_argument(
        "--port",
        type=int,
        required=False,
        default=9000,
        help="The port number to run the gallery server on (default: 9000)",
    )

    # Optional argument for delete mode
    parser.add_argument(
        "--delete-mode",
        required=False,
        choices=["trash", "permanent"],
        default="permanent",
        help="Specify the delete mode for images (default: permanent)",
    )

    parser.add_argument(
        "--load-limit",
        type=int,
        required=False,
        default=1000,
        help="Specify the maximum number of images to load (default: 1000)",
    )

    parser.add_argument(
        "--debug",
        required=False,
        action="store_true",
        default=False,
        help="Specify the debug mode - more verbose and instant reload.",
    )

    return parser
