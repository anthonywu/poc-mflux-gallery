import os
from pathlib import Path
from urllib.parse import quote_plus, unquote_plus
from base64 import urlsafe_b64encode, urlsafe_b64decode
from fasthtml.common import *
from rich import print


app, rt = fast_app()
setup_toasts(app)

GALLERY_DIR = Path(os.environ.get("MFLUX_GALLERY_DIR", "/Users/anthonywu/workspace/flux-output-local"))
os.chdir(GALLERY_DIR)
PAGE_SIZE = 10

def get_page_images():
    tags = []
    for count, img in enumerate(GALLERY_DIR.glob("*/*.png"), 1):
        if count > PAGE_SIZE:
            break
        # img_id = img.name
        src = str(img.relative_to(GALLERY_DIR))
        image_id = urlsafe_b64encode(src.encode("utf8")).decode("utf8")
        tags.append(
            Div(
                Img(src=src, height="50%", width="50%"),
                Form(hx_delete=f"/image/{image_id}")(
                    Button(f"Delete {src}", type="submit"),
                    hx_swap="innerHTML",
                    hx_target=f"#container-image-{count}"
                ),
                id=f"container-image-{count}",
            )
        )
    return tags

@rt("/image/{img_path_b64:str}")
def get(session, img_path_b64: str):
    img_path = urlsafe_b64decode(img_path_b64.encode("utf8")).decode("utf8")
    return FileResponse(img_path)

@rt("/image/{img_path_b64}")
def delete(session, img_path_b64: str):
    img_path = Path(urlsafe_b64decode(img_path_b64.encode("utf8")).decode("utf8"))
    try:
        img_path.unlink()
        add_toast(session, f"Deleted {img_path}")
        return Response(f"Deleted {img_path}")
    except Exception as exc:
        return Response(str(exc))


@rt("/")
def get(session):
    img_elems = [Li(img_tag) for img_tag in get_page_images()]
    num_images = len(img_elems)
    add_toast(session, f"Image Count: {num_images}")
    return Titled(
        "mflux gallery",
        P(f"{num_images} images listed"),
        Ol(*img_elems)
    )

serve()
