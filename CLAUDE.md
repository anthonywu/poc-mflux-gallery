# FastHTML Framework Notes

## Core Concepts

- FastHTML is a Python framework for building web applications with minimal JS
- Uses "HTML-over-the-wire" approach with HTMX integration
- Creates HTML components using Python functions
- Simple routing with decorators

## References

- [FastHTML Documentation](https://docs.fastht.ml)
- [SwiperJS API Documentation](https://swiperjs.com/swiper-api)

## Key Design Patterns

### Application Setup
```python
from fasthtml.common import *
app, rt = fast_app(
    hdrs=(js_scripts, css_styles),  # Optional headers
    static_path=path,               # Static file serving
    live=True/False,                # Live reload
    debug=True/False                # Debug mode
)
serve(host="0.0.0.0", port=9000)    # Start server
```

### Component Construction
- Components created as function calls: `Div(P("Hello"))`
- Attributes via parameters: `Div(cls="container")(content)`
- Nesting via call chaining: `Div()(P()("Text"))`
- Event handling with `hx_` prefixed attributes: `Button(hx_post="/endpoint")`

### Routing System
```python
@rt("/path")
def get(session, param: str):
    return Component()  # Return HTML components directly
```

### Data Loading Pattern
- Create lazily loaded components with HTMX triggers
- Example: `Div(hx_trigger="intersect once", hx_get="/data_endpoint")`

### Image Gallery Implementation
- Uses `Swiper` component for image carousel
- Implements lazy loading for performance
- Handles files with `pathlib.Path` for safety
- Processes images with Pillow

### Event Handling
- Client-side: Custom event listeners for keyboard shortcuts
- Server-side: Route handlers process form submissions
- HTMX for dynamic UI updates without page refresh

## Security Patterns
- Path traversal prevention with `resolve_target` and `relative_to`
- Input validation to prevent jailbreaking
- Static file serving with controlled extensions

## Performance Optimizations
- Image resizing for faster loading
- Lazy loading of images with intersection observer
- Limited batch loading with configurable limits
- Image blurring for inactive carousel slides

## SwiperJS Integration
- Uses SwiperJS for carousel functionality
- Custom parameters for navigation, zoom, keyboard controls
- CSS styling for slide transitions and effects
- Blur effects on non-active slides for focus and privacy

## Code Style Guidelines
- All files should end with a newline character
- Follow consistent indentation (4 spaces)
- Use descriptive variable and function names
- Add type hints for function parameters
