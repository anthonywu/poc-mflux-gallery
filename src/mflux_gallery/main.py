import json
import os
import random
import time
import typing as t
from dataclasses import asdict
from importlib.resources import files
from pathlib import Path

from fasthtml.components import (
    Link,
    Meta,
    P,
    Sup,
)
from fasthtml.core import FT, FastHTML, HtmxResponseHeaders, reg_re_param, serve
from fasthtml.fastapp import fast_app
from fasthtml.toaster import add_toast, setup_toasts
from fasthtml.xtend import Script, Style
from rich import print
from starlette.responses import RedirectResponse, Response

from . import cli, gallery, views
from .config import AppConfig


def _headers() -> tuple[FT, ...]:
    swiper_js = Script(
        src="https://cdn.jsdelivr.net/npm/swiper@11/swiper-element-bundle.min.js"
    )

    custom_handlers = Script(
        files("mflux_gallery").joinpath("assets/gallery.js").read_text(encoding="utf-8")
    )

    custom_css = Style(
        files("mflux_gallery")
        .joinpath("assets/gallery.css")
        .read_text(encoding="utf-8")
    )
    return (
        Meta(name="format-detection", content="telephone=no"),
        Link(
            rel="stylesheet",
            href="https://cdn.jsdelivr.net/gh/0builddotdev/0build@0.6.12/dist/css/kit.min.css",
        ),
        swiper_js,
        custom_handlers,
        custom_css,
    )


def get_created_recency_description(path_st_mtime: float) -> str:
    diff_secs = time.time() - path_st_mtime
    if diff_secs < 60:
        return "just created"
    if diff_secs < 3_600:
        return f"{diff_secs / 60:,.0f} min ago"
    elif diff_secs < 86_400:
        return f"{diff_secs / 3_600:,.0f} hours ago"
    else:
        return f"{diff_secs / 86_400:,.0f} days ago"


def get_image_metadata(img_path: Path) -> t.Any:
    """Load JSON metadata for an image if it exists."""
    json_path = img_path.with_suffix(".json")
    if json_path.exists():
        try:
            with open(json_path, "r") as metadata_file:
                return json.load(metadata_file)
        except (json.JSONDecodeError, IOError):
            return None
    return None


def get_page_images(
    app_gallery: gallery.Gallery,
    config: AppConfig,
    sort_order: t.Literal["newest", "oldest"] = "newest",
    resize_width: int | None = None,
) -> list[FT]:
    reverse = sort_order == "newest"
    matches = sorted(
        app_gallery.iter_all_images(),
        key=lambda path: path.stat().st_mtime,
        reverse=reverse,
    )
    if not matches:
        print(f"No images found in {config.directory}")
        return []
    tags = []
    for count, img_path in enumerate(matches, 1):
        if count > config.load_limit:
            break
        gallery_path = str(img_path.relative_to(config.directory))

        tags.append(
            views.image_card(
                gallery_path,
                count=count,
                load_limit=config.load_limit,
                total_matches=len(matches),
                recency=get_created_recency_description(img_path.stat().st_mtime),
                resize_width=resize_width,
            )
        )
    return tags


def log_notif(
    session: dict[str, t.Any],
    notif: str,
    send_toast: bool = False,
    **toast_kwargs: t.Any,
) -> None:
    print(notif)
    if send_toast:
        add_toast(session, notif, **toast_kwargs)


def gallery_page_response(
    app_gallery: gallery.Gallery,
    config: AppConfig,
    mode: views.GalleryMode,
    resize_width: int | None,
) -> Response | tuple[FT, FT]:
    if resize_width is None:
        path = "/" if mode == "default" else f"/{mode}"
        return RedirectResponse(f"{path}?resize_width={config.resize_max_width}")
    sort_order = "oldest" if mode == "oldest" else "newest"
    img_elems = get_page_images(
        app_gallery, config, sort_order=sort_order, resize_width=resize_width
    )
    if mode == "shuffled":
        random.shuffle(img_elems)
    return views.gallery_page(
        img_elems,
        gallery_dir=config.directory,
        total_images=app_gallery.count_all_images(),
        current_resize=resize_width,
        mode=mode,
    )


def register_image_routes(
    app: FastHTML, config: AppConfig, app_gallery: gallery.Gallery
) -> None:
    @app.route("/image_element")
    async def get(session, gallery_path: str, resize_width: int | None = None):
        try:
            if resize_width is None:
                resize_width = config.resize_max_width
            data_uri_src = await app_gallery.get_image_as_base64(
                gallery_path, resize_max_width=resize_width
            )

            img_path = config.directory / gallery_path
            metadata = get_image_metadata(img_path)

            return views.image_element(data_uri_src, metadata)
        except FileNotFoundError:
            return P(
                f"{gallery_path} is invalid path, does not exist, or has been previously deleted"
            )

    @app.route("/thumbnail")
    async def thumbnail(gallery_path: str):
        try:
            data = await app_gallery.get_thumbnail(gallery_path)
        except gallery.InvalidPathValueError:
            return Response("Invalid image path", status_code=403)
        except OSError:
            return Response("Image unavailable", status_code=404)
        return Response(
            data,
            media_type="image/webp",
            headers={"Cache-Control": "private, max-age=60"},
        )


def register_action_routes(
    app: FastHTML, config: AppConfig, app_gallery: gallery.Gallery
) -> None:
    @app.route("/image_action")
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
                target, success, error_msg = await app_gallery.show_in_finder(
                    gallery_path
                )
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


def register_page_routes(
    app: FastHTML, config: AppConfig, app_gallery: gallery.Gallery
) -> None:
    @app.route("/")
    def get(session, resize_width: int | None = None):
        return gallery_page_response(app_gallery, config, "default", resize_width)

    @app.route("/oldest")
    def get(session, resize_width: int | None = None):
        return gallery_page_response(app_gallery, config, "oldest", resize_width)

    @app.route("/shuffled")
    def get(session, resize_width: int | None = None):
        return gallery_page_response(app_gallery, config, "shuffled", resize_width)


def create_app(config: AppConfig) -> FastHTML:
    """Build an independent gallery application without changing process state."""
    app_gallery = gallery.Gallery(
        config.directory, resize_max_width=config.resize_max_width
    )
    app, _ = fast_app(
        hdrs=_headers(),
        pico=False,
        htmlkw={"class": "z-layout-small", "lang": "en"},
        static_path=config.directory,
        key_fname=str(config.directory / ".sesskey"),
        live=config.debug,
        debug=config.debug,
    )
    reg_re_param("imgext", "ico|gif|GIF|heic|HEIC|jpg|JPG|jpeg|JPEG|png|PNG|webp|WEBP")
    app.static_route_exts(prefix="/", static_path=config.directory, exts="imgext")
    setup_toasts(app)
    app.state.gallery = app_gallery
    app.state.config = config
    register_image_routes(app, config, app_gallery)
    register_action_routes(app, config, app_gallery)
    register_page_routes(app, config, app_gallery)
    return app


_CONFIG_ENV = "MFLUX_GALLERY_CONFIG"


def _create_cli_app() -> FastHTML:
    """Uvicorn factory: reload workers inherit the CLI's resolved configuration."""
    return create_app(AppConfig(**json.loads(os.environ[_CONFIG_ENV])))


def main() -> None:
    args = cli.create_parser().parse_args()
    try:
        config = AppConfig(**vars(args))
    except (OSError, ValueError) as error:
        print(f"Error: {error}")
        raise SystemExit(1) from error
    print(f"Port: {config.port}")
    print(f"Delete Mode: {config.delete_mode}")
    previous_config = os.environ.get(_CONFIG_ENV)
    os.environ[_CONFIG_ENV] = json.dumps(asdict(config), default=str)
    try:
        serve(
            appname="mflux_gallery.main",
            app="_create_cli_app",
            factory=True,
            host=config.host,
            port=config.port,
            reload=config.debug,
            reload_dirs=[str(config.directory)] if config.debug else None,
        )
    finally:
        if previous_config is None:
            os.environ.pop(_CONFIG_ENV, None)
        else:
            os.environ[_CONFIG_ENV] = previous_config


if __name__ == "__main__":
    main()
