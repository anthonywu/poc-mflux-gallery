import json
import os
import random
import time
import typing as t

from fasthtml.common import *
from fasthtml.components import Swiper_Container, Swiper_Slide
from rich import print  # noqa
from starlette.responses import RedirectResponse

from . import cli, gallery

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
    """
    document.addEventListener('delete-successful', function(event) {
        // Get the current active slide index before removal
        const swiper = $("swiper-container")[0].swiper;
        const activeIndex = swiper.activeIndex;
        const slidesCount = swiper.slides.length;

        // Remove the slide from Swiper after a brief delay to ensure DOM update
        setTimeout(function() {
            swiper.removeSlide(activeIndex);

            // If we deleted the last slide, go to the previous one
            if (activeIndex >= slidesCount - 1 && activeIndex > 0) {
                swiper.slideNext();
            }
        }, 100);
    });

    document.addEventListener('keydown', function(event) {
        if (event.key === 'f') {
            $(".swiper-slide-active button.show-in-finder")[0]?.click();
        }
    });

    document.addEventListener('keydown', function(event) {
        if (event.key === 'd') {
            $(".swiper-slide-active button.delete-image")[0]?.click();
        }
    });

    document.addEventListener('keydown', function(event) {
        if (event.key === 'n') {
            event.preventDefault();
            $("swiper-container")[0].swiper.slideNext();
        }
    });

    document.addEventListener('keydown', function(event) {
        if (event.key === 'p') {
            event.preventDefault();
            $("swiper-container")[0].swiper.slidePrev();
        }
    });
    """
)

custom_css = Style(
    """
    @media only screen and (max-width:393px) {
        button.show-in-finder {
            display: none;
        }
        div#keyboard-controls {
            display: none;
        }
    }
    """
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
        hx_vals = {"gallery_path": gallery_path}
        if resize_width is not None:
            hx_vals["resize_width"] = resize_width

        tags.append(
            Details(
                Summary(
                    Mark(Small(f"{count} / {len(matches)} 📂 {gallery_path}")),
                    Small(get_created_recency_description(img_path.stat().st_mtime)),
                    Progress(value=count, max=len(matches)),
                ),
                Div(
                    id=f"lazy-image-{count}",
                    hx_trigger="intersect once throttle:2s",
                    hx_get="/image_element",
                    hx_vals=hx_vals,
                    hx_swap="innerHTML swap:innerHTML transition:fade:200ms:true",
                )(Span(aria_busy=True)(f"Loading {gallery_path}")),
                Div(cls="grid image-actions", style="margin-top: 10px;")(
                    Div(),  # empty filler
                    Div(
                        Form(hx_post="/image_action")(
                            Button(
                                "🔍 Show in Finder ",
                                Kbd("f"),
                                type="submit",
                                cls="secondary show-in-finder",
                                style="width: 100%;",
                            ),
                            Input(
                                type="hidden", name="gallery_path", value=gallery_path
                            ),
                            Input(type="hidden", name="action", value="show-in-finder"),
                        ),
                        hx_swap="none",
                    ),
                    Div(
                        Form(hx_post="/image_action")(
                            Button(
                                "🔥 Delete ",
                                Kbd("d"),
                                type="submit",
                                cls="contrast delete-image",
                                style="width: 100%;",
                            ),
                            Input(
                                type="hidden", name="gallery_path", value=gallery_path
                            ),
                            Input(type="hidden", name="action", value="delete"),
                            Input(type="hidden", name="slide_delete_index", value=str(count)),
                            hx_swap="outerHTML",
                            hx_target=f"#slide-{count}",
                        ),
                    ),
                ),
                id=f"container-image-{count}",
                open=True,
            )
        )
    return tags


app, rt = fast_app(
    hdrs=(
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
        components = [
            Div(
                cls="swiper-zoom-container",
                style="width: 100%; display: flex; justify-content: center;",
            )(
                Img(
                    src=f"{data_uri_src}",
                    style="height: auto; width: auto; max-width: 100%;",
                    cls="swiper-zoom-target",
                )
            )
        ]

        # Add metadata display if available
        if metadata:
            metadata_components = [
                Div(
                    Strong("Guidance: "),
                    Code(
                        metadata.get("guidance", "n/a"), style="white-space: pre-wrap;"
                    ),
                    Strong("Steps: "),
                    Code(metadata.get("steps", "n/a"), style="white-space: pre-wrap;"),
                    style="margin-top: 10px;",
                ),
                Div(
                    Strong("Prompt: "),
                    Code(metadata.get("prompt", "n/a"), style="white-space: pre-wrap;"),
                    style="margin-top: 10px;",
                ),
            ]

            components.append(
                Div(
                    *metadata_components,
                    style="padding: 10px; border-radius: 5px; margin-top: 10px;",
                )
            )

        return Div(*components)
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
            return Response(""), HtmxResponseHeaders(trigger="delete-successful")
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
    num_images = len(img_elems)
    # Determine current resize width for dropdown
    current_resize = resize_width if resize_width is not None else args.resize_max_width

    return Title(GALLERY_DIR), Div(
        Nav()(
            Ul()(
                Li()(Code(GALLERY_DIR, style="font-size: 0.5em;"), Sup(num_images)),
                Li(A(href=f"/?resize_width={current_resize}")("Latest ▶️")),
                Li(A(href=f"/oldest?resize_width={current_resize}")("Oldest ◀️")),
                Li(A(href=f"/shuffled?resize_width={current_resize}")("Shuffled 🔀")),
                Li()(
                    Label(
                        "Max Width: ", For="resize-select", style="margin-right: 5px;"
                    ),
                    Select(
                        id="resize-select",
                        name="resize_width",
                        onchange=f"window.location.href = '{'/' if mode == 'default' else '/' + mode}?resize_width=' + this.value",
                    )(
                        Option("256px", value="256", selected=(current_resize == 256)),
                        Option("512px", value="512", selected=(current_resize == 512)),
                        Option("768px", value="768", selected=(current_resize == 768)),
                        Option(
                            "1024px", value="1024", selected=(current_resize == 1024)
                        ),
                    ),
                ),
            )
        ),
        Swiper_Container(
            *[Swiper_Slide(elem, lazy=True, id=f"slide-{i}") for i, elem in enumerate(img_elems, 1)],
            # https://swiperjs.com/swiper-api#parameters
            keyboard_enabled=True,
            lazy_preload_prev_next=True,
            # centered_slides=True,
            navigation=False,
            pagination=False,
            scroolbar=False,
            speed=100,
            zoom=True,
        ),
        Footer(
            Div(id="keyboard-controls")(
                H4("Keyboard Controls: "),
                Ul(
                    Li(Kbd("d"), Span("Delete image and advance slide")),
                    Li(Kbd("f"), Span("Show in Finder")),
                ),
            )
        ),
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
    serve(host=args.host, port=args.port, reload=args.debug)


if __name__ == "__main__":
    main()
