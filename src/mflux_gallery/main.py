import json
import os
import random
import time
import typing as t
from importlib.resources import files

from fasthtml.components import (
    Meta,
    P,
    Sup,
)
from fasthtml.core import HtmxResponseHeaders, reg_re_param, serve
from fasthtml.fastapp import fast_app
from fasthtml.toaster import add_toast, setup_toasts
from fasthtml.xtend import Script, Style
from rich import print  # noqa
from starlette.responses import RedirectResponse, Response

from . import cli, gallery, views

parser = cli.create_parser()
args = parser.parse_args()

GALLERY_DIR = args.directory.resolve()

if not GALLERY_DIR.exists():
    print(f"Error: Directory '{GALLERY_DIR}' does not exist.")
    exit(1)

if not GALLERY_DIR.is_dir():
    print(f"Error: '{GALLERY_DIR}' is not a directory.")
    exit(1)

try:
    app_gallery = gallery.Gallery(GALLERY_DIR, resize_max_width=args.resize_max_width)
    os.chdir(GALLERY_DIR)
except (FileNotFoundError, PermissionError) as e:
    print(f"Error accessing directory '{GALLERY_DIR}': {e}")
    exit(1)

swiper_js = Script(
    src="https://cdn.jsdelivr.net/npm/swiper@11/swiper-element-bundle.min.js"
)
cash_js = Script(src="https://cdn.jsdelivr.net/npm/cash-dom/dist/cash.min.js")
jquery_js = Script(src="https://code.jquery.com/jquery-3.7.1.min.js")

custom_handlers = Script(
    files("mflux_gallery").joinpath("assets/gallery.js").read_text(encoding="utf-8")
)

custom_css = Style(
    files("mflux_gallery").joinpath("assets/gallery.css").read_text(encoding="utf-8")
)


def get_created_recency_description(path_st_mtime):
    diff_secs = time.time() - path_st_mtime
    if diff_secs < 60:
        return "just created"
    if diff_secs < 3_600:
        return f"{diff_secs / 60:,.0f} min ago"
    elif diff_secs < 86_400:
        return f"{diff_secs / 3_600:,.0f} hours ago"
    else:
        return f"{diff_secs / 86_400:,.0f} days ago"


def get_image_metadata(img_path):
    """Load JSON metadata for an image if it exists."""
    json_path = img_path.with_suffix(".json")
    if json_path.exists():
        try:
            with open(json_path, "r") as f:
                data = json.load(f)
                return data
        except (json.JSONDecodeError, IOError):
            return None
    return None


def get_page_images(sort_order="newest", resize_width=None):
    reverse = sort_order == "newest"
    matches = sorted(
        list(iter(app_gallery)), key=lambda _: _.stat().st_mtime, reverse=reverse
    )
    if not matches:
        print(f"No images found in {GALLERY_DIR}")
        return []
    tags = []
    for count, img_path in enumerate(matches, 1):
        if count > args.load_limit:
            break
        gallery_path = str(img_path.relative_to(GALLERY_DIR))

        # Prepare hx_vals with gallery_path and optional resize_width
        tags.append(
            views.image_card(
                gallery_path,
                count,
                args.load_limit,
                len(matches),
                get_created_recency_description(img_path.stat().st_mtime),
                resize_width,
            )
        )
    return tags


app, rt = fast_app(
    hdrs=(
        Meta(name="format-detection", content="telephone=no"),
        jquery_js,
        swiper_js,
        custom_handlers,
        custom_css,
    ),
    static_path=args.directory,
    live=args.debug,
    debug=args.debug,
)
reg_re_param("imgext", "ico|gif|GIF|heic|HEIC|jpg|JPG|jpeg|JPEG|png|PNG|webp|WEBP")
app.static_route_exts(prefix="/", static_path=args.directory, exts="imgext")
setup_toasts(app)

reg_re_param("path_segments", r"[^\.]+")


@rt("/image_element")
async def get(session, gallery_path: str, resize_width: int = None):
    try:
        # Use provided resize_width or fall back to the default
        if resize_width is None:
            resize_width = args.resize_max_width
        data_uri_src = await app_gallery.get_image_as_base64(
            gallery_path, resize_max_width=resize_width
        )

        # Load metadata if available
        img_path = GALLERY_DIR / gallery_path
        metadata = get_image_metadata(img_path)

        # Build the image display components
        return views.image_element(data_uri_src, metadata)
    except FileNotFoundError:
        return P(
            f"{gallery_path} is invalid path, does not exist, or has been previously deleted"
        )


def log_notif(session, notif, send_toast=False, **toast_kwargs):
    print(notif)
    if send_toast:
        add_toast(session, notif, **toast_kwargs)


@rt("/image_action")
async def post(session, action: str, gallery_path: str):
    action = action.strip().lower()
    if action not in ["delete", "show-in-finder"]:
        return Response(f"{action=} not supported", status_code=403)

    try:
        if action == "delete":
            target, success = await app_gallery.delete_item(
                gallery_path, delete_other_suffixes=[".json"]
            )
            if success:
                notif = f"Deleted {target.as_posix()!r}"
                log_notif(session, notif, typ="success")
            else:
                notif = f"Does not exist: {target.as_posix()!r}"
                log_notif(session, notif, typ="warning")

            # Count remaining images (actual total, not load-limited)
            remaining_images = app_gallery.count_all_images()

            # Return empty response with trigger for slide removal, plus updated counter via OOB
            return (
                Sup(remaining_images, id="photo-counter", hx_swap_oob="true"),
                HtmxResponseHeaders(trigger="delete-successful"),
            )
        elif action == "show-in-finder":
            target, success, error_msg = await app_gallery.show_in_finder(gallery_path)
            if success:
                notif = f"Opened {target.as_posix()!r} in Finder."
                log_notif(session, notif, send_toast=True, typ="success")
                return Response(notif)
            else:
                notif = f"{error_msg}"
                log_notif(session, notif, send_toast=True, typ="error")
                return Response(notif, status_code=500)
    except gallery.InvalidPathValueError:
        return Response(f"cannot jailbreak to {gallery_path}", status_code=403)


def _gallery_page(
    title,
    img_elems,
    mode: t.Literal["default", "shuffled", "oldest"] = "default",
    resize_width: int = None,
):
    # Get actual total count of images in gallery
    total_images = app_gallery.count_all_images()
    # Determine current resize width for dropdown
    current_resize = resize_width if resize_width is not None else args.resize_max_width

    return views.gallery_page(
        title, img_elems, GALLERY_DIR, total_images, current_resize, mode
    )


@rt("/")
def get(session, resize_width: int = None):
    # Redirect to include resize_width parameter if not present
    if resize_width is None:
        return RedirectResponse(f"/?resize_width={args.resize_max_width}")
    img_elems = get_page_images(resize_width=resize_width)
    return _gallery_page(
        "gallery", img_elems, mode="default", resize_width=resize_width
    )


@rt("/oldest")
def get(session, resize_width: int = None):
    # Redirect to include resize_width parameter if not present
    if resize_width is None:
        return RedirectResponse(f"/oldest?resize_width={args.resize_max_width}")
    img_elems = get_page_images(sort_order="oldest", resize_width=resize_width)
    return _gallery_page("gallery", img_elems, mode="oldest", resize_width=resize_width)


@rt("/shuffled")
def get(session, resize_width: int = None):
    # Redirect to include resize_width parameter if not present
    if resize_width is None:
        return RedirectResponse(f"/shuffled?resize_width={args.resize_max_width}")
    img_elems = get_page_images(resize_width=resize_width)
    random.shuffle(img_elems)
    return _gallery_page(
        "gallery", img_elems, mode="shuffled", resize_width=resize_width
    )


def main():
    print(f"Port: {args.port}")
    print(f"Delete Mode: {args.delete_mode}")
    serve(
        appname="mflux_gallery.main", host=args.host, port=args.port, reload=args.debug
    )


if __name__ == "__main__":
    main()
