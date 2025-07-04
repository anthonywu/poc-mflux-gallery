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
        default="127.0.0.1",
        help="The host address to run the gallery server on (default: 127.0.0.1)",
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
        "-d",
        required=False,
        choices=["trash", "permanent"],
        default="permanent",
        help="Specify the delete mode for images (default: permanent)",
    )

    parser.add_argument(
        "--load-limit",
        "-l",
        type=int,
        required=False,
        default=100,
        help="Specify the maximum number of images to load (default: 100)",
    )

    parser.add_argument(
        "--debug",
        required=False,
        action="store_true",
        default=False,
        help="Specify the debug mode - more verbose and instant reload.",
    )

    parser.add_argument(
        "--resize-max-width",
        "-w",
        type=int,
        required=False,
        default=512,
        help="Specify the maximum width for image resizing (default: 512)",
    )

    return parser
