import os
import random
import time
import typing as t

from fasthtml.common import *
from fasthtml.components import Swiper_Container, Swiper_Slide
from rich import print  # noqa

import cli
import gallery

parser = cli.create_parser()
args = parser.parse_args()


app_gallery = gallery.Gallery(
    GALLERY_DIR := args.directory.resolve(), resize_max_width=args.resize_max_width
)
os.chdir(GALLERY_DIR)

swiper_js = Script(
    src="https://cdn.jsdelivr.net/npm/swiper@11/swiper-element-bundle.min.js"
)
cash_js = Script(src="https://cdn.jsdelivr.net/npm/cash-dom/dist/cash.min.js")
jquery_js = Script(src="https://code.jquery.com/jquery-3.7.1.min.js")

custom_handlers = Script(
    """
    document.addEventListener('delete-successful', function(event) {
        $("swiper-container")[0].swiper.slideNext();
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


def get_page_images():
    matches = sorted(
        list(iter(app_gallery)), key=lambda _: _.stat().st_mtime, reverse=True
    )
    if not matches:
        print(f"No images found in {GALLERY_DIR}")
        return []
    tags = []
    for count, img_path in enumerate(matches, 1):
        if count > args.load_limit:
            break
        gallery_path = str(img_path.relative_to(GALLERY_DIR))
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
                    hx_vals={"gallery_path": gallery_path},
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
                                style="width: 100%;"
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
                            hx_swap="innerHTML",
                            hx_target=f"#container-image-{count}",
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
async def get(session, gallery_path: str):
    try:
        data_uri_src = await app_gallery.get_image_as_base64(gallery_path)
        return Img(src=f"{data_uri_src}", style="height: auto; width: auto;")
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
            return Response(notif), HtmxResponseHeaders(trigger="delete-successful")
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


def _gallery_page(title, img_elems, mode: t.Literal["default", "shuffled"] = "default"):
    num_images = len(img_elems)
    return Title(GALLERY_DIR), Div(
        Nav()(
            Ul()(
                Li()(Code(GALLERY_DIR, style="font-size: 0.5em;"), Sup(num_images)),
                Li(A(href="/")("Latest ▶️")),
                Li(A(href="/shuffled")("Shuffled 🔀")),
            )
        ),
        Swiper_Container(
            *[Swiper_Slide(_, lazy=True) for _ in img_elems],
            # https://swiperjs.com/swiper-api#parameters
            keyboard_enabled=True,
            lazy_preload_prev_next=True,
            # centered_slides=True,
            navigation=False,
            pagination=False,
            scroolbar=False,
            speed=100,
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
def get(session):
    return _gallery_page("gallery", get_page_images(), mode="default")


@rt("/shuffled")
def get(session):
    img_elems = get_page_images()
    random.shuffle(img_elems)
    return _gallery_page("gallery", img_elems, mode="shuffled")


print(f"Port: {args.port}")
print(f"Delete Mode: {args.delete_mode}")
serve(host=args.host, port=args.port, reload=args.debug)
