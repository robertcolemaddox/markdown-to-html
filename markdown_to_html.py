#!/usr/bin/env python3
"""Markdown to HTML converter with optional CSS injection and live preview."""

from __future__ import annotations

import argparse
import html
import http.server
import threading
import time
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import markdown
import yaml
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


@dataclass
class Document:
    """Parsed Markdown document and its metadata."""

    body: str
    metadata: dict[str, Any]


def parse_front_matter(raw: str) -> Document:
    """Extract YAML front matter delimited by --- lines.

    A document without front matter is returned unchanged.
    Invalid YAML raises ValueError with a useful message.
    """
    lines = raw.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return Document(raw, {})

    end = next(
        (index for index in range(1, len(lines)) if lines[index].strip() == "---"),
        None,
    )
    if end is None:
        return Document(raw, {})

    yaml_text = "".join(lines[1:end])
    body = "".join(lines[end + 1 :])

    try:
        metadata = yaml.safe_load(yaml_text) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML front matter: {exc}") from exc

    if not isinstance(metadata, dict):
        raise ValueError("YAML front matter must contain a mapping/object.")

    return Document(body, metadata)


class MarkdownConverter:
    """Convert Markdown documents into complete HTML documents."""

    DEFAULT_EXTENSIONS = [
        "fenced_code",
        "tables",
        "toc",
        "sane_lists",
        "nl2br",
    ]

    @classmethod
    def parse_file(
        cls,
        input_path: str | Path,
        style_path: str | Path | None = None,
        title: str | None = None,
    ) -> str:
        """Read, render, and wrap a Markdown file as a complete HTML document."""
        source = Path(input_path)
        if not source.is_file():
            raise FileNotFoundError(f"Markdown file not found: {source}")

        raw = source.read_text(encoding="utf-8")
        document = parse_front_matter(raw)

        page_title = title or document.metadata.get("title") or source.stem
        page_title = html.escape(str(page_title), quote=True)

        body = markdown.markdown(
            document.body,
            extensions=cls.DEFAULT_EXTENSIONS,
            output_format="html5",
        )

        css = ""
        if style_path:
            stylesheet = Path(style_path)
            if not stylesheet.is_file():
                raise FileNotFoundError(f"Stylesheet not found: {stylesheet}")
            css = (
                '<style data-source="markdown-to-html">\n'
                f"{stylesheet.read_text(encoding='utf-8')}\n"
                "</style>"
            )

        description = document.metadata.get("description")
        description_tag = ""
        if description:
            description_tag = (
                f'<meta name="description" content="{html.escape(str(description), quote=True)}">'
            )

        return f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    {description_tag}
    <title>{page_title}</title>
    {css}
</head>
<body>
<main class="markdown-body">
{body}
</main>
</body>
</html>
"""


class PreviewHandler(FileSystemEventHandler):
    """Rebuild the preview when the source Markdown or stylesheet changes."""

    def __init__(
        self,
        input_path: Path,
        output_path: Path,
        style_path: Path | None,
    ) -> None:
        self.input_path = input_path.resolve()
        self.output_path = output_path.resolve()
        self.style_path = style_path.resolve() if style_path else None
        self._last_build = 0.0

    def _matches(self, changed: Path) -> bool:
        changed = changed.resolve()
        return changed == self.input_path or changed == self.style_path

    def on_modified(self, event) -> None:
        if event.is_directory:
            return
        changed = Path(event.src_path)
        if not self._matches(changed):
            return

        # Editors commonly save by producing multiple filesystem events.
        now = time.monotonic()
        if now - self._last_build < 0.15:
            return
        self._last_build = now

        try:
            build_html(self.input_path, self.output_path, self.style_path)
            print(f"✓ Rebuilt {self.output_path}")
        except Exception as exc:
            print(f"✗ Build failed: {exc}")


def build_html(
    input_path: str | Path,
    output_path: str | Path,
    style_path: str | Path | None = None,
    title: str | None = None,
) -> Path:
    """Convert one Markdown file and write its HTML output."""
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    rendered = MarkdownConverter.parse_file(input_path, style_path, title)
    destination.write_text(rendered, encoding="utf-8")
    return destination


def serve_preview(directory: Path, port: int) -> http.server.ThreadingHTTPServer:
    """Start a local HTTP server rooted at *directory*."""

    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:
            print(f"[server] {format % args}")

    handler = lambda *args, **kwargs: QuietHandler(
        *args, directory=str(directory), **kwargs
    )
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def default_output(input_path: Path) -> Path:
    """Return the conventional .html path next to the source file."""
    return input_path.with_suffix(".html")


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="markdown-to-html",
        description="Convert Markdown files into standalone HTML documents.",
    )
    parser.add_argument("input_file", type=Path, help="Markdown source file.")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="HTML destination. Defaults to <input>.html.",
    )
    parser.add_argument(
        "-s",
        "--style",
        type=Path,
        help="Optional CSS file to embed into the generated HTML.",
    )
    parser.add_argument(
        "--title",
        help="Override the document title (front matter title otherwise wins).",
    )
    parser.add_argument(
        "-w",
        "--watch",
        action="store_true",
        help="Watch the Markdown/CSS files and serve a live local preview.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Preview server port (default: 8000).",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not automatically open the live preview in a browser.",
    )
    return parser


def run_watch(
    input_path: Path,
    output_path: Path,
    style_path: Path | None,
    port: int,
    open_browser: bool,
) -> int:
    build_html(input_path, output_path, style_path)
    server = serve_preview(output_path.parent, port)
    url = f"http://127.0.0.1:{port}/{output_path.name}"

    print(f"✓ Preview: {url}")
    if open_browser:
        webbrowser.open(url)

    observer = Observer()
    handler = PreviewHandler(input_path, output_path, style_path)
    observer.schedule(handler, str(input_path.parent), recursive=False)
    if style_path and style_path.parent != input_path.parent:
        observer.schedule(handler, str(style_path.parent), recursive=False)
    observer.start()

    print("Watching for changes. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping preview.")
    finally:
        observer.stop()
        observer.join()
        server.shutdown()
        server.server_close()

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = make_parser()
    args = parser.parse_args(argv)

    input_path = args.input_file.resolve()
    output_path = (args.output or default_output(input_path)).resolve()
    style_path = args.style.resolve() if args.style else None

    try:
        if args.watch:
            return run_watch(
                input_path,
                output_path,
                style_path,
                args.port,
                not args.no_browser,
            )

        result = build_html(input_path, output_path, style_path, args.title)
        print(f"✓ Converted {input_path} -> {result}")
        return 0
    except (FileNotFoundError, ValueError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
