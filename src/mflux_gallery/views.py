"""Gallery HTML components; callers supply all filesystem and configuration data."""

from pathlib import Path
from typing import Any, Literal

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


def image_actions(gallery_path: str, count: int) -> FT:
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
        ),
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
                hx_swap="outerHTML",
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
    resize_width: int | None = None,
) -> FT:
    hx_vals = {"gallery_path": gallery_path}
    if resize_width is not None:
        hx_vals["resize_width"] = resize_width
    return Details(
        Summary(
            Mark(
                Small(f"{count} / of batch size {load_limit} / total: {total_matches}")
            ),
            Small(recency),
        ),
        Div(
            id=f"lazy-image-{count}",
            hx_trigger="intersect once throttle:2s",
            hx_get="/image_element",
            hx_vals=hx_vals,
            hx_swap="innerHTML swap:innerHTML transition:fade:200ms:true",
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
        image_actions(gallery_path, count),
        cls="image-card z-card",
        id=f"container-image-{count}",
        open=True,
    )


def metadata_panel(metadata: dict[str, Any]) -> FT:
    metadata_components = [
        Div(
            Strong("Prompt: "),
            Code(metadata.get("prompt", "n/a"), style="white-space: pre-wrap;"),
            style="margin-top: 10px;",
        )
    ]
    return Details(
        Summary(
            "Metadata (",
            Strong("Guidance: "),
            metadata.get("guidance", "n/a"),
            " / ",
            Strong("Steps: "),
            metadata.get("steps", "n/a"),
            ")",
            style="cursor: pointer; font-weight: bold;",
        ),
        Div(
            *metadata_components,
            style="padding: 10px; border-radius: 5px; margin-top: 10px;",
        ),
        cls="metadata-section",
        style="margin-top: 10px;",
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
                    href=f"/?resize_width={current_resize}",
                    cls="z-button z-button-ghost",
                    aria_current="page" if mode == "default" else None,
                )
            ),
            Li(
                A(
                    "Oldest",
                    href=f"/oldest?resize_width={current_resize}",
                    cls="z-button z-button-ghost",
                    aria_current="page" if mode == "oldest" else None,
                )
            ),
            Li(
                A(
                    "Shuffled",
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
                    onchange=f"window.location.href = '{('/' if mode == 'default' else '/' + mode)}?resize_width=' + this.value",
                )(
                    Option("256px", value="256", selected=current_resize == 256),
                    Option("512px", value="512", selected=current_resize == 512),
                    Option("768px", value="768", selected=current_resize == 768),
                    Option("1024px", value="1024", selected=current_resize == 1024),
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


def gallery_controls() -> FT:
    return Footer(
        Div(id="mobile-controls")(
            Button(
                "← 10",
                onclick="event.preventDefault(); const swiper = document.querySelector('swiper-container').swiper; swiper.slideTo(Math.max(0, swiper.activeIndex - 10));",
                cls="z-button z-button-default",
                style="min-width: 80px;",
            ),
            Button(
                "10 →",
                onclick="event.preventDefault(); const swiper = document.querySelector('swiper-container').swiper; swiper.slideTo(Math.min(swiper.slides.length - 1, swiper.activeIndex + 10));",
                cls="z-button z-button-default",
                style="min-width: 80px;",
            ),
        ),
        Details(id="keyboard-controls")(
            Summary(H4("Keyboard Controls ('h' to toggle)")),
            Div(id="keyboard-controls-hotkey-list")(
                Ul(
                    Li(Kbd("n"), Span("Next image")),
                    Li(Kbd("p"), Span("Previous image")),
                    Li(Kbd("j"), Span("Jump back 10 slides")),
                    Li(Kbd("k"), Span("Jump forward 10 slides")),
                    Li(Kbd("a"), Span("Go to first slide")),
                    Li(Kbd("e"), Span("Go to last slide")),
                    Li(Kbd("d"), Span("Delete image and advance slide")),
                    Li(Kbd("f"), Span("Show in Finder")),
                    Li(Kbd("m"), Span("Toggle metadata visibility")),
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
) -> tuple[FT, FT]:
    return (
        Title(gallery_dir),
        Div(
            Div(
                Div(Small("MFLUX / IMAGE LIBRARY", cls="eyebrow"), H1("Gallery")),
                Div(
                    Code(gallery_dir),
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
            Swiper_Container(
                *[
                    Swiper_Slide(elem, lazy=True, id=f"slide-{i}")
                    for i, elem in enumerate(img_elems, 1)
                ],
                keyboard_enabled=True,
                lazy_preload_prev_next=True,
                navigation=False,
                pagination=False,
                scroolbar=False,
                speed=100,
                zoom=True,
            ),
            gallery_controls(),
            cls="gallery-shell",
        ),
    )
