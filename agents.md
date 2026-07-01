# AGENTS.md

# X Traversal

## Project Overview

X Traversal is a local desktop application for collecting assets from ticket folders.

The application scans selected ticket directories, finds approved deliverable folders, copies supported assets into an output folder, then optimizes those assets by:

- converting PDFs to PNG
- resizing large images
- resizing HD videos
- generating a report of copied files

---

## Technology

- Python 3.14
- Tkinter
- Pillow
- pypdfium2
- FFmpeg / FFprobe
- PyInstaller
- uv (package and project manager)

---

## Dependency Management

This project uses **uv** as the Python package and project manager.

Always use `uv` for dependency management. Do not use `pip`, `poetry`, or other package managers unless explicitly requested.

Common commands:

```bash
# Install a dependency
uv add <package> --system-certs

# Remove a dependency
uv remove <package> --system-certs

# Sync the environment
uv sync --system-certs
```

Always include the `--system-certs` flag when running `uv` commands.

## Project Structure

app.py
    Desktop UI
    User interaction
    Progress display
    Starts the processing pipeline

pipeline.py
    File traversal
    Asset collection
    Image/PDF/video processing
    Structured logging

---

## Architecture Rules

- UI code belongs in `app.py`.
- Processing logic belongs in `pipeline.py`.
- Keep UI and processing logic separated.
- Keep functions focused and easy to read.

---

## Development Guidelines

Prefer:

- small targeted changes
- readable code
- minimal complexity
- backward compatibility
- simple helper functions over large abstractions

Avoid:

- unnecessary refactoring
- changing existing behaviour unless requested
- introducing new dependencies
- changing the output folder structure
- changing processing order unless requested

---

## UI Guidelines

When modifying the UI:

- preserve existing functionality
- improve appearance without adding features
- keep the application lightweight
- maintain consistent spacing, typography and colors
- avoid large framework-like abstractions

---

## Processing Guidelines

The processing pipeline should remain deterministic.

Current stages are:

1. Discover source folders
2. Copy supported assets
3. Convert PDFs
4. Resize images
5. Resize videos
6. Generate report

Do not reorder these stages unless explicitly requested.

---

## Packaging

Development

```bash
uv run app.py
```

Build

```bash
uv run pyinstaller \                               
  --clean \
  --noconfirm \
  --windowed \
  --name "X Traversal" \
  --icon=logo.icns \
  --add-data "logo.png:." \
  --add-binary "$(which ffmpeg):." \
  --add-binary "$(which ffprobe):." \
  app.py
```

The application is distributed as a standalone PyInstaller executable.

FFmpeg and FFprobe are bundled with the application.

---

## Agent Instructions

Before making changes:

- understand the existing implementation
- prefer modifying existing code over rewriting it
- preserve compatibility with PyInstaller
- keep cross-platform behaviour intact
- avoid duplicate code
- ask before introducing new functionality

When responding with code:

- provide complete code only for the sections being modified
- clearly indicate where changes should be applied
- do not rewrite unrelated files