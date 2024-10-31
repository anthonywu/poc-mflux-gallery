import argparse
import os
import random
import sys
from pathlib import Path

from fasthtml.common import *
from rich import print  # noqa


def create_parser():
    parser = argparse.ArgumentParser(
        prog='genai-gallery',
        description='Manage an AI image gallery.'
    )

    # Positional argument for the directory
    parser.add_argument(
        'directory',
        type=Path,
        help='The directory containing the images for the gallery'
    )

    # Optional argument for the host
    parser.add_argument(
        '--host',
        type=str,
        required=False,
        default='0.0.0.0',
        help='The port number to run the gallery server on (default: 0.0.0.0)'
    )

    # Optional argument for the port
    parser.add_argument(
        '--port',
        type=int,
        required=False,
        default=9000,
        help='The port number to run the gallery server on (default: 9000)'
    )

    # Optional argument for delete mode
    parser.add_argument(
        '--delete-mode',
        required=False,
        choices=['trash', 'permanent'],
        default='permanent',
        help='Specify the delete mode for images (default: permanent)'
    )

    parser.add_argument(
        '--debug',
        required=False,
        action='store_true',
        default=False,
        help='Specify the debug mode - more verbose and instant reload.'
    )

    return parser

parser = create_parser()
args = parser.parse_args()


GALLERY_DIR = args.directory.resolve()
os.chdir(GALLERY_DIR)
LOAD_LIMIT = 1000

PHOTO_SUFFIXES = [".jpg", ".jpeg", ".png"]

def iter_glob_photos(suffixes=PHOTO_SUFFIXES) -> Path:
    count = 0
    for suf in suffixes:
        for _ in GALLERY_DIR.rglob(f"*{suf}", case_sensitive=False):
            if count <= LOAD_LIMIT:
                yield _
            count += 1


def get_page_images():
    matches = sorted(
        list(iter_glob_photos()),
        key=lambda _: _.stat().st_mtime,
        reverse=True
    )
    if not matches:
        print(f"No images found in {GALLERY_DIR}")
        sys.exit(1)
    tags = []
    for count, img_path in enumerate(matches, 1):
        if count > LOAD_LIMIT:
            break
        gallery_path = str(img_path.relative_to(GALLERY_DIR))
        tags.append(
            Div(
                Div(
                    id=f"lazy-image-{count}",
                    hx_trigger="revealed throttle:2s",
                    hx_get="/image_element",
                    hx_vals={"gallery_path": gallery_path},
                    hx_swap="innerHTML swap:innerHTML transition:fade:200ms:true",
                )(
                    P(f"image #{count} at"),
                    Code(gallery_path)
                ),
                Form(hx_post="/image_action")(
                    Button(f"Delete {img_path}", type="submit"),
                    Input(type="hidden", name="gallery_path", value=gallery_path),
                    Input(type="hidden", name="action", value="delete"),
                    hx_swap="innerHTML",
                    hx_target=f"#container-image-{count}",
                    style="""border: 1px;""".strip()
                ),
                id=f"container-image-{count}",
            )
        )
    return tags


app, rt = fast_app(static_path=args.directory, live=args.debug, debug=args.debug)
reg_re_param("imgext", "ico|gif|GIF|heic|HEIC|jpg|JPG|jpeg|JPEG|png|PNG|webp|WEBP")
app.static_route_exts(prefix="/", static_path=args.directory, exts='imgext')
setup_toasts(app)

reg_re_param("path_segments", r'[^\.]+')

@rt("/image_element")
def get(session, gallery_path: str):
    return Img(src=f"{gallery_path}", style="height: 50vh")


@rt("/image_action")
async def post(session, action: str, gallery_path: str):
    if action not in ["delete"]:
        return Response(f"{action=} not supported", status_code=403)

    target = (GALLERY_DIR / gallery_path).resolve()
    try:
        # safety: do not allow user to traverse above the gallery dir
        target.relative_to(GALLERY_DIR)
    except ValueError:
        return Response(f"cannot jailbreak to {target=}", status_code=403)

    if action.lower() == "delete":
        if target.exists():
            target.unlink()
            notif = f"Deleted {target.as_posix()!r}"
            add_toast(session, notif, typ="success")
        else:
            notif = f"Does not exist: {target.as_posix()!r}"
            add_toast(session, notif, typ="warning")

    return Response(notif)


def _gallery_page(title, img_elems):
    num_images = len(img_elems)
    return Titled(
        title,
        P(Span("Directory"), Code(GALLERY_DIR)),
        P(f"{num_images} images listed"),
        Ol(*img_elems)
    )

@rt("/")
def get(session):
    img_elems = [Li(img_tag) for img_tag in get_page_images()]
    return _gallery_page("mflux gallery", img_elems)

@rt("/shuffled")
def get(session):
    img_elems = [Li(img_tag) for img_tag in get_page_images()]
    random.shuffle(img_elems)
    return _gallery_page("mflux gallery - shuffled", img_elems)


print(f"Port: {args.port}")
print(f"Delete Mode: {args.delete_mode}")
serve(
    host=args.host,
    port=args.port,
    reload=args.debug
)
