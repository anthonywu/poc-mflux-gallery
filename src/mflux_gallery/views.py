"""Gallery HTML components; callers supply all filesystem and configuration data."""

from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlencode

from fasthtml.components import (
    H1,
    H4,
    A,
    Button,
    Code,
    Details,
    Div,
    Footer,
    Form,
    Img,
    Input,
    Kbd,
    Label,
    Li,
    Mark,
    Nav,
    Option,
    Select,
    Small,
    Span,
    Strong,
    Summary,
    Sup,
    Swiper_Container,
    Swiper_Slide,
    Title,
    Ul,
)
from fasthtml.core import FT

GalleryMode = Literal["default", "shuffled", "oldest"]


def image_actions(
    gallery_path: str, count: int, *, finder_available: bool = False
) -> FT:
    return Div(cls="image-actions")(
        Div(),
        Div(
            Form(hx_post="/image_action")(
                Button(
                    "Show in Finder ",
                    Kbd("f"),
                    type="submit",
                    cls="z-button z-button-default show-in-finder",
                    style="width: 100%;",
                ),
                Input(type="hidden", name="gallery_path", value=gallery_path),
                Input(type="hidden", name="action", value="show-in-finder"),
            ),
            hx_swap="none",
        )
        if finder_available
        else None,
        Div(
            Form(hx_post="/image_action")(
                Button(
                    "Delete ",
                    Kbd("d"),
                    type="submit",
                    cls="z-button z-button-default delete-image",
                    style="width: 100%;",
                ),
                Input(type="hidden", name="gallery_path", value=gallery_path),
                Input(type="hidden", name="action", value="delete"),
                Input(type="hidden", name="slide_delete_index", value=str(count)),
                hx_swap="none",
                hx_target=f"#slide-{count}",
            )
        ),
    )


def image_card(
    gallery_path: str,
    *,
    count: int,
    load_limit: int,
    total_matches: int,
    recency: str,
    finder_available: bool = False,
    resize_width: int | None = None,
) -> FT:
    image_params = {"gallery_path": gallery_path}
    if resize_width is not None:
        image_params["resize_width"] = resize_width
    return Details(
        Summary(
            Mark(
                Small(f"{count} / of batch size {load_limit} / total: {total_matches}")
            ),
            Small(recency),
        ),
        Div(
            id=f"lazy-image-{count}",
            cls="image-loader",
            data_image_url="/image_element?" + urlencode(image_params),
            aria_busy="true",
        )(
            Div(cls="skeleton-container")(
                Div(cls="skeleton-loader"), Small(cls="skeleton-text short")
            )
        ),
        Div(
            Button(
                Span(gallery_path, cls="image-path-label"),
                Span("Copy filename", cls="copy-hint", aria_live="polite"),
                type="button",
                cls="copy-filename",
                data_filename=Path(gallery_path).name,
                aria_label="Copy filename to clipboard",
            ),
            cls="image-filename",
        ),
        image_actions(gallery_path, count, finder_available=finder_available),
        cls="image-card z-card",
        id=f"container-image-{count}",
        open=True,
    )


def metadata_panel(metadata: dict[str, Any]) -> FT:
    fields = (
        ("guidance", "Guidance"),
        ("steps", "Steps"),
        ("seed", "Seed"),
        ("model", "Model"),
    )
    return Details(
        Summary("Image details", Span(" · prompt & settings", cls="metadata-hint")),
        Div(
            *[
                Span(
                    Span(label, cls="metadata-key"),
                    " ",
                    str(metadata[key]),
                    cls="metadata-value",
                )
                for key, label in fields
                if key in metadata
            ],
            cls="metadata-values",
        ),
        Div(
            Strong("Prompt"),
            Button(
                "Copy prompt",
                type="button",
                cls="z-button z-button-ghost copy-prompt",
                aria_live="polite",
            ),
            cls="prompt-heading",
        ),
        Code(str(metadata.get("prompt", "n/a")), cls="prompt-text"),
        cls="metadata-section",
    )


def image_element(data_uri_src: str, metadata: dict[str, Any] | None) -> FT:
    components = [
        Div(
            cls="swiper-zoom-container",
            style="width: 100%; display: flex; justify-content: center;",
        )(
            Img(
                src=data_uri_src,
                style="height: auto; width: auto; max-width: 100%;",
                cls="swiper-zoom-target",
            )
        )
    ]
    if metadata:
        components.append(metadata_panel(metadata))
    return Div(*components)


def gallery_navigation(mode: GalleryMode, current_resize: int) -> FT:
    return Nav(aria_label="Gallery controls")(
        Ul()(
            Li(
                A(
                    "Latest",
                    Kbd("A", cls="nav-shortcut"),
                    aria_keyshortcuts="a",
                    href=f"/?resize_width={current_resize}",
                    cls="z-button z-button-ghost",
                    aria_current="page" if mode == "default" else None,
                )
            ),
            Li(
                A(
                    "Oldest",
                    Kbd("Z", cls="nav-shortcut"),
                    aria_keyshortcuts="z",
                    href=f"/oldest?resize_width={current_resize}",
                    cls="z-button z-button-ghost",
                    aria_current="page" if mode == "oldest" else None,
                )
            ),
            Li(
                A(
                    "Shuffled",
                    Kbd("S", cls="nav-shortcut"),
                    aria_keyshortcuts="s",
                    href=f"/shuffled?resize_width={current_resize}",
                    cls="z-button z-button-ghost",
                    aria_current="page" if mode == "shuffled" else None,
                )
            ),
            Li()(
                Label("Max Width: ", For="resize-select", style="margin-right: 5px;"),
                Select(
                    id="resize-select",
                    name="resize_width",
                    cls="z-select",
                    title="Max width: 1 = 256px, 2 = 512px, 3 = 768px, 4 = 1024px",
                    aria_keyshortcuts="1 2 3 4",
                    onchange=f"window.location.href = '{('/' if mode == 'default' else '/' + mode)}?resize_width=' + this.value",
                )(
                    Option("256px · 1", value="256", selected=current_resize == 256),
                    Option("512px · 2", value="512", selected=current_resize == 512),
                    Option("768px · 3", value="768", selected=current_resize == 768),
                    Option("1024px · 4", value="1024", selected=current_resize == 1024),
                ),
            ),
            Li()(
                Button(
                    "🌙",
                    cls="z-button z-button-default theme-toggle",
                    aria_label="Toggle dark/light mode",
                    onclick="toggleTheme()",
                    title="Toggle dark/light mode",
                )
            ),
        )
    )


def browse_controls() -> FT:
    return Div(
        Button(
            "←",
            type="button",
            data_step="-1",
            aria_label="Previous image",
            title="Previous image (p)",
            cls="z-button z-button-default",
        ),
        Button(
            "−10",
            type="button",
            data_step="-10",
            aria_label="Back ten images",
            title="Back ten (j)",
            cls="z-button z-button-ghost jump-control",
        ),
        Span("0 of 0", id="slide-position", role="status", aria_live="polite"),
        Button(
            "+10",
            type="button",
            data_step="10",
            aria_label="Forward ten images",
            title="Forward ten (k)",
            cls="z-button z-button-ghost jump-control",
        ),
        Button(
            "→",
            type="button",
            data_step="1",
            aria_label="Next image",
            title="Next image (n)",
            cls="z-button z-button-default",
        ),
        Button(
            "Focus",
            type="button",
            data_action="focus",
            aria_pressed="false",
            title="Focus mode (v); Escape to exit",
            cls="z-button z-button-ghost",
        ),
        Button(
            "Thumbnails",
            type="button",
            data_action="filmstrip",
            aria_expanded="false",
            aria_controls="filmstrip",
            cls="z-button z-button-ghost",
        ),
        cls="browse-controls",
        role="group",
        aria_label="Image navigation",
    )


def gallery_controls(*, finder_available: bool = False) -> FT:
    return Footer(
        Details(id="keyboard-controls")(
            Summary(H4("Keyboard Controls ('h' to toggle)")),
            Div(id="keyboard-controls-hotkey-list")(
                Ul(
                    Li(Kbd("n"), Span("Next image")),
                    Li(Kbd("p"), Span("Previous image")),
                    Li(Kbd("j"), Span("Jump back 10 slides")),
                    Li(Kbd("k"), Span("Jump forward 10 slides")),
                    Li(Kbd("Home"), Span("Go to first slide")),
                    Li(Kbd("A / Z / S"), Span("Latest / Oldest / Shuffled")),
                    Li(Kbd("e"), Span("Go to last slide")),
                    Li(Kbd("d"), Span("Delete image and advance slide")),
                    Li(Kbd("f"), Span("Show in Finder")) if finder_available else None,
                    Li(Kbd("m"), Span("Toggle metadata visibility")),
                    Li(Kbd("v"), Span("Focus mode; Escape to exit")),
                    Li(Kbd("1–4"), Span("Change image resolution")),
                )
            ),
        ),
    )


def gallery_page(
    img_elems: list[FT],
    *,
    gallery_dir: Path,
    total_images: int,
    current_resize: int,
    mode: GalleryMode = "default",
    finder_available: bool = False,
) -> tuple[FT, FT]:
    return (
        Title(gallery_dir),
        Div(
            Div(
                Div(Small("MFLUX / IMAGE LIBRARY", cls="eyebrow"), H1("Gallery")),
                Div(
                    Code(gallery_dir, title=str(gallery_dir)),
                    Span(
                        Sup(total_images, id="photo-counter"),
                        " images",
                        cls="image-count",
                    ),
                    cls="gallery-location",
                ),
                cls="gallery-heading",
            ),
            gallery_navigation(mode, current_resize),
            browse_controls(),
            Swiper_Container(
                *[
                    Swiper_Slide(elem, lazy=True, id=f"slide-{i}")
                    for i, elem in enumerate(img_elems, 1)
                ],
                keyboard_enabled=True,
                auto_height=True,
                navigation=False,
                pagination=False,
                scrollbar=False,
                speed=100,
                zoom=True,
            ),
            Div("No images in this batch", id="empty-gallery", hidden=bool(img_elems)),
            Div(
                Button(
                    "← 9",
                    type="button",
                    data_step="-9",
                    aria_label="Previous thumbnail group",
                    cls="z-button z-button-ghost",
                ),
                Div(id="filmstrip-items", role="group", aria_label="Image thumbnails"),
                Button(
                    "9 →",
                    type="button",
                    data_step="9",
                    aria_label="Next thumbnail group",
                    cls="z-button z-button-ghost",
                ),
                id="filmstrip",
                hidden=True,
            ),
            gallery_controls(finder_available=finder_available),
            cls="gallery-shell",
        ),
    )
