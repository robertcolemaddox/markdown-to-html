import argparse
import os
import sys
import time
import webbrowser
from http.server import SimpleHTTPRequestHandler, HTTPServer
import threading
import markdown
import yaml
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class MarkdownConverter:
    """Core translation engine for parsing Markdown, styles, and front matter."""

    @staticmethod
    def parse_file(input_path, style_path=None):
        """Reads Markdown, parses YAML metadata, applies CSS, and returns final HTML."""
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Target markdown file not found: {input_path}")

        with open(input_path, 'r', encoding='utf-8') as f:
            raw_content = f.read()

        front_matter = {}
        markdown_text = raw_content

        # Extract YAML Front Matter
        if raw_content.startswith('---'):
            try:
                parts = raw_content.split('---', 2)
                if len(parts) >= 3:
                    front_matter = yaml.safe_load(parts[1]) or {}
                    markdown_text = parts[2]
            except Exception as e:
                print(f"⚠️ Warning: Failed to parse YAML front matter. {e}")

        # Render Markdown core
        body_content = markdown.markdown(markdown_text, extensions=['fenced_code', 'tables'])

        # Resolve Page Title
        page_title = front_matter.get('title', os.path.splitext(os.path.basename(input_path))[0])

        # Read Inline Custom CSS Injection
        css_styles = ""
        if style_path and os.path.exists(style_path):
            with open(style_path, 'r', encoding='utf-8') as css_file:
                css_styles = f"<style>{css_file.read()}</style>"

        # Compile Semantic Production HTML Document
        full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page_title}</title>
    {css_styles}
</head>
<body>
    <main class="markdown-body">
        {body_content}
    </main>
</body>
</html>"""
        return full_html


class LivePreviewHandler(FileSystemEventHandler):
    """Monitors file changes to trigger seamless background builds."""
    def __init__(self, input_file, output_file, style_file):
        self.input_file = os.path.abspath(input_file)
        self.output_file = output_file
        self.style_file = os.path.abspath(style_file) if style_file else None

    def on_modified(self, event):
        target_path = os.path.abspath(event.src_path)
        if target_path in [self.input_file, self.style_file]:
            print(f"🔄 Change detected in {os.path.basename(target_path)}. Rebuilding...")
            try:
                html = MarkdownConverter.parse_file(self.input_file, self.style_file)
                with open(self.output_file, 'w', encoding='utf-8') as f:
                    f.write(html)
            except Exception as e:
                print(f"❌ Dynamic Build Failed: {e}")


def serve_preview_browser(directory, port=8000):
    """Spins up a lightweight background server for local browser testing."""
    os.chdir(directory)
    server = HTTPServer(('localhost', port), SimpleHTTPRequestHandler)
    print(f"🌐 Live Preview Hosting at: http://localhost:{port}/preview.html")
    webbrowser.open(f"http://localhost:{port}/preview.html")
    server.serve_forever()


def main():
    parser = argparse.ArgumentParser(
        description="🚀 MarkdownToHTML - An Enterprise-grade CLI static renderer portfolio project."
    )
    parser.add_argument("input_file", help="Path to your markdown source file (.md)")
    parser.add_argument("-o", "--output", help="Destination path for outputting the compiled HTML document")
    parser.add_argument("-s", "--style", help="Path to a custom layout stylesheet (.css) to inject directly into the header")
    parser.add_argument("-w", "--watch", action="store_true", help="Launch interactive server with real-time preview refreshes")

    args = parser.parse_args()

    out_dir = os.path.dirname(os.path.abspath(args.output)) if args.output else os.getcwd()
    out_name = os.path.basename(args.output) if args.output else "preview.html" if args.watch else None
    final_output_path = os.path.join(out_dir, out_name) if out_name else None

    try:
        if args.watch:
            final_output_path = os.path.join(out_dir, "preview.html")
            os.makedirs(out_dir, exist_ok=True)

            initial_html = MarkdownConverter.parse_file(args.input_file, args.style)
            with open(final_output_path, 'w', encoding='utf-8') as f:
                f.write(initial_html)

            server_thread = threading.Thread(target=serve_preview_browser, args=(out_dir, 8000), daemon=True)
            server_thread.start()

            event_handler = LivePreviewHandler(args.input_file, final_output_path, args.style)
            observer = Observer()
            observer.schedule(event_handler, path=os.path.dirname(os.path.abspath(args.input_file)) or '.', recursive=False)
            observer.start()

            print("⚡ Real-time file observation running. Press Ctrl+C to stop.")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nStopping safe services. Goodbye!")
                observer.stop()
            observer.join()

        else:
            html_payload = MarkdownConverter.parse_file(args.input_file, args.style)
            if final_output_path:
                os.makedirs(os.path.dirname(final_output_path), exist_ok=True)
                with open(final_output_path, 'w', encoding='utf-8') as f:
                    f.write(html_payload)
                print(f"🚀 Render complete. Validated markup document exported to: {final_output_path}")
            else:
                sys.stdout.write(html_payload)

    except Exception as err:
        print(f"❌ Execution Failure: {err}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
