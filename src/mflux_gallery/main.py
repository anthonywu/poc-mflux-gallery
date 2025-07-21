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
    // Dark mode handling
    function initTheme() {
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme) {
            document.documentElement.setAttribute('data-theme', savedTheme);
        }
        updateThemeToggleIcon();
    }

    function toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        updateThemeToggleIcon();
    }

    function updateThemeToggleIcon() {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark' ||
                      (!document.documentElement.getAttribute('data-theme') &&
                       window.matchMedia('(prefers-color-scheme: dark)').matches);
        const btn = document.querySelector('.theme-toggle');
        if (btn) {
            btn.textContent = isDark ? '☀️' : '🌙';
        }
    }

    // Initialize theme on load
    document.addEventListener('DOMContentLoaded', initTheme);

    // Metadata expansion state handling
    function initMetadataState() {
        const savedState = localStorage.getItem('metadataExpanded');
        // Only apply saved state if it exists (respecting default collapsed state)
        if (savedState !== null) {
            document.querySelectorAll('details.metadata-section').forEach(details => {
                if (savedState === 'true') {
                    details.setAttribute('open', '');
                } else {
                    details.removeAttribute('open');
                }
            });
        }
    }

    function toggleMetadataState(event) {
        const isOpen = event.target.hasAttribute('open');
        localStorage.setItem('metadataExpanded', isOpen);

        // Sync state across all metadata sections
        document.querySelectorAll('details.metadata-section').forEach(details => {
            if (isOpen) {
                details.setAttribute('open', '');
            } else {
                details.removeAttribute('open');
            }
        });
    }

    // Watch for dynamically loaded metadata sections
    const metadataObserver = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            mutation.addedNodes.forEach((node) => {
                if (node.nodeType === 1) { // Element node
                    const metadataDetails = node.querySelector('details.metadata-section');
                    if (metadataDetails) {
                        const savedState = localStorage.getItem('metadataExpanded');
                        // Only apply saved state if it exists
                        if (savedState !== null) {
                            if (savedState === 'true') {
                                metadataDetails.setAttribute('open', '');
                            } else {
                                metadataDetails.removeAttribute('open');
                            }
                        }
                        metadataDetails.addEventListener('toggle', toggleMetadataState);
                    }
                }
            });
        });
    });

    // Start observing when DOM is loaded
    document.addEventListener('DOMContentLoaded', () => {
        initMetadataState();
        metadataObserver.observe(document.body, { childList: true, subtree: true });

        // Add event listeners to existing metadata sections
        document.querySelectorAll('details.metadata-section').forEach(details => {
            details.addEventListener('toggle', toggleMetadataState);
        });
    });

    // Image gallery handlers
    document.addEventListener('delete-successful', function(event) {
        // Get the current active slide index before removal
        const swiper = $("swiper-container")[0].swiper;
        const activeIndex = swiper.activeIndex;
        const slidesCount = swiper.slides.length;

        // Clear loading state on delete button before slide removal
        const activeSlide = document.querySelector('.swiper-slide-active');
        if (activeSlide) {
            const deleteButton = activeSlide.querySelector('button.delete-image');
            if (deleteButton) {
                setButtonLoading(deleteButton, false);
            }
        }

        // Remove the slide from Swiper after a brief delay to ensure DOM update
        setTimeout(function() {
            // Store whether we're at the last slide before removal
            const isLastSlide = activeIndex === slidesCount - 1;

            // Remove the slide
            swiper.removeSlide(activeIndex);

            // After removing a slide:
            // - If we were at the last slide, we're now at the new last slide (no action needed)
            // - If we weren't at the last slide, we need to stay at the same index (which now shows the next image)
            // Swiper automatically handles this, but we need to ensure the active slide is visible
            if (!isLastSlide) {
                // Force update to ensure the slide is properly displayed
                swiper.slideTo(activeIndex, 0);
            }
        }, 100);
    });

    // Button loading state handling
    function setButtonLoading(button, isLoading) {
        if (isLoading) {
            button.classList.add('loading');
            button.disabled = true;
        } else {
            button.classList.remove('loading');
            button.disabled = false;
        }
    }

    function showButtonFeedback(button, type, duration = 1500) {
        button.classList.remove('loading');
        button.classList.add(type);
        setTimeout(() => {
            button.classList.remove(type);
            button.disabled = false;
        }, duration);
    }

    // Intercept form submissions for loading states
    document.addEventListener('submit', function(event) {
        const form = event.target;
        const button = form.querySelector('button[type="submit"]');

        if (button && (button.classList.contains('delete-image') || button.classList.contains('show-in-finder'))) {
            setButtonLoading(button, true);

            // For delete action, add optimistic animation
            if (button.classList.contains('delete-image')) {
                const slide = button.closest('.swiper-slide');
                if (slide) {
                    slide.classList.add('deleting');
                }
            }
        }
    });

    // Handle successful actions
    document.addEventListener('htmx:afterRequest', function(event) {
        const button = event.detail.elt.querySelector('button[type="submit"]');
        if (button) {
            if (event.detail.successful) {
                if (button.classList.contains('show-in-finder')) {
                    showButtonFeedback(button, 'success');
                } else if (button.classList.contains('delete-image')) {
                    // Delete is successful, but button will be removed with the slide
                    setButtonLoading(button, false);
                }
            } else {
                showButtonFeedback(button, 'error');
            }
        }
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

    document.addEventListener('keydown', function(event) {
        if (event.key === 'j') {
            event.preventDefault();
            const swiper = $("swiper-container")[0].swiper;
            const targetIndex = Math.max(0, swiper.activeIndex - 10);
            swiper.slideTo(targetIndex);
        }
    });

    document.addEventListener('keydown', function(event) {
        if (event.key === 'k') {
            event.preventDefault();
            const swiper = $("swiper-container")[0].swiper;
            const targetIndex = Math.min(swiper.slides.length - 1, swiper.activeIndex + 10);
            swiper.slideTo(targetIndex);
        }
    });

    document.addEventListener('keydown', function(event) {
        if (event.key === 'a') {
            event.preventDefault();
            const swiper = $("swiper-container")[0].swiper;
            swiper.slideTo(0);
        }
    });

    document.addEventListener('keydown', function(event) {
        if (event.key === 'e') {
            event.preventDefault();
            const swiper = $("swiper-container")[0].swiper;
            swiper.slideTo(swiper.slides.length - 1);
        }
    });

    document.addEventListener('keydown', function(event) {
        if (event.key === 'm' || event.key === 'M') {
            event.preventDefault();
            // Toggle the metadata in the active slide
            const activeSlide = document.querySelector('.swiper-slide-active');
            if (activeSlide) {
                const metadataSection = activeSlide.querySelector('details.metadata-section');
                if (metadataSection) {
                    // Simulate a click on the details element to trigger the toggle event
                    metadataSection.open = !metadataSection.open;
                    metadataSection.dispatchEvent(new Event('toggle'));
                }
            }
        }
    });

    // Resolution switching hotkeys (1-4)
    document.addEventListener('keydown', function(event) {
        const resolutionMap = {
            '1': '256',
            '2': '512',
            '3': '768',
            '4': '1024'
        };

        if (resolutionMap[event.key]) {
            event.preventDefault();
            const newResolution = resolutionMap[event.key];
            const currentPath = window.location.pathname;
            const currentSearch = new URLSearchParams(window.location.search);

            // Update the resize_width parameter
            currentSearch.set('resize_width', newResolution);

            // Navigate to the new URL
            window.location.href = currentPath + '?' + currentSearch.toString();
        }
    });
    """
)

custom_css = Style(
    """
    /* CSS Variables for Design System */
    :root {
        /* Light mode colors */
        --bg-primary: #ffffff;
        --bg-secondary: #f5f5f5;
        --bg-tertiary: #e9ecef;
        --text-primary: #212529;
        --text-secondary: #6c757d;
        --text-tertiary: #adb5bd;
        --border-color: #dee2e6;
        --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
        --shadow-md: 0 4px 6px rgba(0,0,0,0.1);

        /* Spacing system (8px base) */
        --space-xs: 4px;
        --space-sm: 8px;
        --space-md: 16px;
        --space-lg: 24px;
        --space-xl: 32px;

        /* Transitions */
        --transition-fast: 150ms ease;
        --transition-normal: 250ms ease;
        --transition-slow: 350ms ease;
    }

    /* Dark mode colors */
    [data-theme="dark"] {
        --bg-primary: #1a1a1a;
        --bg-secondary: #2d2d2d;
        --bg-tertiary: #3d3d3d;
        --text-primary: #f8f9fa;
        --text-secondary: #adb5bd;
        --text-tertiary: #6c757d;
        --border-color: #495057;
        --shadow-sm: 0 1px 2px rgba(0,0,0,0.3);
        --shadow-md: 0 4px 6px rgba(0,0,0,0.4);
    }

    /* Auto-detect system preference */
    @media (prefers-color-scheme: dark) {
        :root:not([data-theme="light"]) {
            --bg-primary: #1a1a1a;
            --bg-secondary: #2d2d2d;
            --bg-tertiary: #3d3d3d;
            --text-primary: #f8f9fa;
            --text-secondary: #adb5bd;
            --text-tertiary: #6c757d;
            --border-color: #495057;
            --shadow-sm: 0 1px 2px rgba(0,0,0,0.3);
            --shadow-md: 0 4px 6px rgba(0,0,0,0.4);
        }
    }

    /* Apply theme colors */
    body {
        background-color: var(--bg-primary);
        color: var(--text-primary);
        transition: background-color var(--transition-normal), color var(--transition-normal);
    }

    nav {
        background-color: var(--bg-secondary);
        border-bottom: 1px solid var(--border-color);
        box-shadow: var(--shadow-sm);
        transition: all var(--transition-normal);
    }

    details {
        background-color: var(--bg-secondary);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: var(--space-md);
        margin-bottom: var(--space-md);
        transition: all var(--transition-normal);
    }

    details summary {
        color: var(--text-primary);
        transition: color var(--transition-normal);
    }

    code {
        background-color: var(--bg-tertiary);
        color: var(--text-primary);
        border: 1px solid var(--border-color);
        transition: all var(--transition-normal);
    }

    button {
        transition: all var(--transition-fast);
    }

    button:hover {
        transform: translateY(-1px);
        box-shadow: var(--shadow-md);
    }

    /* Dark mode toggle button */
    .theme-toggle {
        background: transparent;
        border: none;
        color: var(--text-primary);
        cursor: pointer;
        font-size: 1.2em;
        padding: var(--space-sm);
        border-radius: 4px;
        transition: all var(--transition-fast);
    }

    .theme-toggle:hover {
        background-color: var(--bg-tertiary);
        transform: none;
        box-shadow: none;
    }

    /* Swiper adjustments for dark mode */
    .swiper-slide {
        background-color: var(--bg-primary);
    }

    /* Footer adjustments */
    footer {
        background-color: var(--bg-secondary);
        border-top: 1px solid var(--border-color);
        padding: var(--space-lg);
        transition: all var(--transition-normal);
    }

    /* Metadata section styling */
    details[open] > div {
        animation: fadeIn var(--transition-normal);
    }

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-5px); }
        to { opacity: 1; transform: translateY(0); }
    }

    /* Mobile responsiveness */
    @media only screen and (max-width:393px) {
        button.show-in-finder {
            display: none;
        }
        div#keyboard-controls {
            display: none;
        }
    }

    /* Focus states for accessibility */
    button:focus-visible,
    a:focus-visible,
    select:focus-visible {
        outline: 2px solid var(--text-secondary);
        outline-offset: 2px;
    }

    /* Button loading states */
    button.loading {
        position: relative;
        color: transparent !important;
        pointer-events: none;
        opacity: 0.8;
    }

    button.loading::after {
        content: "";
        position: absolute;
        width: 16px;
        height: 16px;
        top: 50%;
        left: 50%;
        margin-left: -8px;
        margin-top: -8px;
        border: 2px solid var(--text-secondary);
        border-radius: 50%;
        border-top-color: transparent;
        animation: spinner 0.6s linear infinite;
    }

    @keyframes spinner {
        to { transform: rotate(360deg); }
    }

    /* Optimistic delete animation */
    .swiper-slide.deleting {
        animation: fadeOutScale var(--transition-normal) forwards;
    }

    @keyframes fadeOutScale {
        to {
            opacity: 0;
            transform: scale(0.9);
        }
    }

    /* Success feedback */
    button.success {
        background-color: #28a745 !important;
        color: white !important;
        transition: background-color var(--transition-fast);
    }

    /* Error feedback */
    button.error {
        background-color: #dc3545 !important;
        color: white !important;
        transition: background-color var(--transition-fast);
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
                    Mark(Small(f"{count} / of batch size {args.load_limit} / total: {len(matches)}")),
                    Small(get_created_recency_description(img_path.stat().st_mtime)),
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
                        P(f"📂 {gallery_path}"),
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
                            Input(
                                type="hidden",
                                name="slide_delete_index",
                                value=str(count),
                            ),
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
                    Strong("Prompt: "),
                    Code(metadata.get("prompt", "n/a"), style="white-space: pre-wrap;"),
                    style="margin-top: 10px;",
                ),
            ]

            components.append(
                Details(
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

            # Count remaining images (actual total, not load-limited)
            remaining_images = app_gallery.count_all_images()

            # Return empty response with trigger for slide removal, plus updated counter via OOB
            return (
                Sup(remaining_images, id="photo-counter", hx_swap_oob="true"),
                HtmxResponseHeaders(trigger="delete-successful")
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

    return Title(GALLERY_DIR), Div(
        Div()(Code(GALLERY_DIR, style="font-size: 0.5em;"), Sup(total_images, id="photo-counter")),
        Nav()(
            Ul()(
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
                Li()(
                    Button(
                        "🌙",
                        cls="theme-toggle",
                        onclick="toggleTheme()",
                        title="Toggle dark/light mode",
                    )
                ),
            )
        ),
        Swiper_Container(
            *[
                Swiper_Slide(elem, lazy=True, id=f"slide-{i}")
                for i, elem in enumerate(img_elems, 1)
            ],
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
                    Li(Kbd("n"), Span("Next image")),
                    Li(Kbd("p"), Span("Previous image")),
                    Li(Kbd("j"), Span("Jump back 10 slides")),
                    Li(Kbd("k"), Span("Jump forward 10 slides")),
                    Li(Kbd("a"), Span("Go to first slide")),
                    Li(Kbd("e"), Span("Go to last slide")),
                    Li(Kbd("d"), Span("Delete image and advance slide")),
                    Li(Kbd("f"), Span("Show in Finder")),
                    Li(Kbd("m"), Span("Toggle metadata visibility")),
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
