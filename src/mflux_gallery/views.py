"""Gallery HTML components; callers supply all filesystem and configuration data."""

from fasthtml.components import (
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
    P,
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


def image_actions(gallery_path, count):
    return Div(cls="grid image-actions", style="margin-top: 10px;")(
        Div(),
        Div(
            Form(hx_post="/image_action")(
                Button(
                    "🔍 Show in Finder ",
                    Kbd("f"),
                    type="submit",
                    cls="secondary show-in-finder",
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
                    "🔥 Delete ",
                    Kbd("d"),
                    type="submit",
                    cls="contrast delete-image",
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
    gallery_path, count, load_limit, total_matches, recency, resize_width=None
):
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
        Div(P(f"📂 {gallery_path}", cls="image-path-label")),
        image_actions(gallery_path, count),
        id=f"container-image-{count}",
        open=True,
    )


def metadata_panel(metadata):
    metadata_components = [
        Div(
            Strong("Prompt: "),
            Code(metadata.get("prompt", "n/a"), style="white-space: pre-wrap;"),
            style="margin-top: 10px;",
        )
    ]
    return Details(
        Summary(
            "📋 Metadata (",
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


def image_element(data_uri_src, metadata):
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


def gallery_navigation(mode, current_resize):
    return Nav()(
        Ul()(
            Li(A(href=f"/?resize_width={current_resize}")("Latest ▶️")),
            Li(A(href=f"/oldest?resize_width={current_resize}")("Oldest ◀️")),
            Li(A(href=f"/shuffled?resize_width={current_resize}")("Shuffled 🔀")),
            Li()(
                Label("Max Width: ", For="resize-select", style="margin-right: 5px;"),
                Select(
                    id="resize-select",
                    name="resize_width",
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
                    cls="theme-toggle",
                    onclick="toggleTheme()",
                    title="Toggle dark/light mode",
                )
            ),
        )
    )


def gallery_controls():
    return Footer(
        Div(id="mobile-controls")(
            Button(
                "⏪ -10",
                onclick="event.preventDefault(); const swiper = document.querySelector('swiper-container').swiper; swiper.slideTo(Math.max(0, swiper.activeIndex - 10));",
                cls="secondary",
                style="min-width: 80px;",
            ),
            Button(
                "+10 ⏩",
                onclick="event.preventDefault(); const swiper = document.querySelector('swiper-container').swiper; swiper.slideTo(Math.min(swiper.slides.length - 1, swiper.activeIndex + 10));",
                cls="secondary",
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
    title, img_elems, gallery_dir, total_images, current_resize, mode="default"
):
    return (
        Title(gallery_dir),
        Div(
            Div()(
                Code(gallery_dir, style="font-size: 0.5em;"),
                Sup(total_images, id="photo-counter"),
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
        ),
    )
