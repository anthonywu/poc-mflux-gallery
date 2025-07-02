This project's name and repo path is subject to change. The repo name is prefixed with `poc-` to communicate that this is a proof of concept that may not ever publish to PyPi and if/when ready the repo may be renamed as the mission scope increases or decreases.

# Image collection manager

A responsive web-based image gallery viewer for browsing and pruning local image collections, specifically motivated by the need to quickly browse and prune images from a collection of photos, screenshots, downloaded image artifacts, optimized for decision speed via quick thumb/keyboard interactions.

Originally motivated by the need to manage generated images from the mflux image generator project, I realized it can actually be applied to any image collection such as managing my macOS `~/Desktop` and `~/Downloads` folders.

Design is minimalist and optimized for decision speed, informed by my prior work building the YouTube content policy review tools when I worked there in the early days.

## Features

- 🖼️ **Image Gallery Browsing**: Display images from any local directory with swiper-based UI
- 🗑️ **Image Management**: Delete images directly from the UI (one tap or one key press)
- ⌨️ **Keyboard Controls**: Navigate and decide with keyboard shortcuts
- 🔍 **Finder Integration**: Show/reveal images in Finder (macOS)

- 📸 **Multi-format Support**: Works with JPEG, PNG, GIF, HEIC, and more
- 🔄 **Multiple View Modes**: Browse by latest (modification time) or shuffled order
- 📱 **Responsive Design**: Works on desktop and mobile devices
- 🔍 **Image Zooming**: Zoom in on images for detail viewing
- 📊 **Progress Indicators**: See your current position in the gallery

### Performance Optimizations

- 📲 **Optimized for Remote/Mobile**: Images are inlined as base64 data to reduce number of HTTP connections
- 🚀 **Bandwidth Optimization**: Images are resized to a configurable maximum width to save bandwidth on slower connections

## Installation

### Option 1: Install as a CLI tool with uv

You can install mflux-gallery directly as a command-line tool using `uv`:

```bash
# Install from GitHub repository
uv tool install git+https://github.com/anthonywu/poc-mflux-gallery.git

# The tool will be available as 'mflux-gallery' command
mflux-gallery /path/to/images
```

### Option 2: Clone and run locally

```bash
# Clone the repository
git clone https://github.com/anthonywu/poc-mflux-gallery.git mflux-gallery
cd mflux-gallery

# Create virtual environment and install dependencies with uv
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package in development mode
uv pip install -e .
```

## Usage

### If installed with uv tool:

```bash
mflux-gallery /path/to/images [OPTIONS]
```

### If running from source:

```bash
python -m mflux_gallery.main /path/to/images [OPTIONS]
```

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--host` | Host address to bind server | 0.0.0.0 |
| `--port` | Port number for the server | 9000 |
| `--delete-mode` | How to handle deletion ("trash" or "permanent") | permanent |
| `--load-limit` | Maximum number of images to load | 1000 |
| `--debug` | Enable debug mode (verbose output, live reload) | False |
| `--resize-max-width` | Maximum width for resizing gallery images | 512 |

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `d` | Delete current image |
| `f` | Show in Finder (macOS) |
| `n` | Next image |
| `p` | Previous image |

Additionally, all [SwiperJS Keyboard Controls](https://swiperjs.com/swiper-api#keyboard-control) are available.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.
