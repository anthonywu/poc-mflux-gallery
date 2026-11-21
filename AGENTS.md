# Agent Guidelines for mflux-gallery

## Build, Lint, and Test Commands

### Environment Setup
```bash
# Sync the environment with locked dependencies
uv sync --locked

# Run the application
uv run mflux-gallery /path/to/images [OPTIONS]
# or
uv run python -m mflux_gallery.main /path/to/images [OPTIONS]
```

### Code Quality
```bash
# Lint and auto-fix issues
ruff check --fix .

# Format code
ruff format .

# Run both linting and formatting
ruff check --fix . && ruff format .
```

### Testing
Tests use `pytest`, placed in `tests/` mirroring `src/`.

```bash
# Run all tests
uv run pytest tests/ -v

# To run a single test
uv run pytest tests/test_module.py::test_function -v
```

- Prefer module-level test functions with plain `assert` for new tests
- Legacy `unittest.TestCase` classes are still collected and run by pytest
- Use `pytest-asyncio` fixtures/functions when testing async methods

## Code Style Guidelines

### Imports
- Standard library imports first, then third-party, then local (relative)
- `typing` imported as `t`: `import typing as t`
- Use `pathlib.Path` over `os.path`
- Star imports allowed for `fasthtml.common` (F403/F405 ignored)
- Group related imports together

### Formatting and Style
- Use 4-space indentation
- All files must end with a newline character
- Follow PEP8 and Google Python Style Guide
- Ruff configuration ignores F403, F405 (star imports), F811 (reused route defs)
- Keep docstrings minimal - use self-documenting function names

### Type Hints
- Use Python 3.11+ syntax: `list[str]`, `dict[str, int]`, not `typing.List`
- Use `t.Literal["option1", "option2"]` for string literals
- Use union syntax `str | Path` not `typing.Union`
- Always add return type hints to functions
- Always add type hints to function parameters

### Naming Conventions
- Classes: PascalCase (`Gallery`, `InvalidPathValueError`)
- Functions/Methods: snake_case (`get_page_images`, `delete_item`)
- Constants: UPPER_SNAKE_CASE (`DEFAULT_PHOTO_SUFFIXES`, `GALLERY_DIR`)
- Variables: snake_case
- Private members: underscore prefix (`_count_cache`, `invalidate_count_cache`)

### Error Handling
- Define custom exceptions inheriting from ValueError or Exception
- Use specific exception types in try/except blocks
- Chain exceptions with `from e` context when appropriate
- Raise `InvalidPathValueError` for path traversal attempts
- Validate user inputs to prevent security issues (path jailbreaking)

### Async and Concurrency
- Use async/await for I/O operations (file access, subprocess calls)
- Async methods should be `async def` with proper await statements
- Context managers for resource management (file handles, image operations)

### Code Patterns
- Walrus operator `:=` when value needed for both if-check and usage
- Prefer builtin generics and PEP 604 unions (`list[str]`, `str | Path`) over `typing.List`/`typing.Union`; import from `typing` only what has no builtin equivalent (e.g., `t.Literal`, `t.Callable`)
- Lazy loading for expensive operations (e.g., `count_all_images` caching)
- FastHTML components created via function calls: `Div()(P("text"))`
- Use `pathlib.Path` methods like `.resolve()`, `.relative_to()` for security

### Security
- Always resolve and validate file paths to prevent directory traversal
- Use `.relative_to(gallery_dir)` to check path boundaries
- Never trust user input - validate and sanitize all inputs
- Use `pathlib.Path` over string concatenation for file operations

### Web Framework (FastHTML)
- Components are Python functions: `Div(P("content"))`
- Attributes via parameters: `Button(hx_post="/endpoint")`
- Route handlers use decorators: `@rt("/path")`
- Return HTML components directly from routes
- HTMX attributes for dynamic behavior: `hx_get`, `hx_post`, `hx_vals`

### Dependencies
- Check pyproject.toml before adding new dependencies
- Run `uv pip install --dry-run <package>` to review transitive dependencies
- Keep dependencies alphabetically sorted in pyproject.toml
- Minimal dependencies - prefer stdlib over third-party when possible
