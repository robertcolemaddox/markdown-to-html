# Markdown to HTML

A small, dependency-light Python CLI that converts Markdown into complete HTML documents.

It supports:

- Standard Markdown headings, paragraphs, emphasis, links, lists, blockquotes, and images
- Fenced code blocks
- Tables
- YAML front matter
- Embedded custom CSS
- Automatic HTML document generation
- Live preview with file watching
- A local browser preview server
- A test suite suitable for GitHub Actions

The goal is to be a useful, understandable project rather than a large framework.

## Requirements

- Python 3.10+
- `markdown`
- `PyYAML`
- `watchdog`

## Installation

```powershell
git clone https://github.com/robertcolemaddox/markdown-to-html.git
cd markdown-to-html

py -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install -r requirements.txt
```

## Basic usage

Convert `document.md` to `document.html`:

```powershell
python markdown_to_html.py document.md
```

Specify an output file:

```powershell
python markdown_to_html.py document.md -o site/index.html
```

Embed a stylesheet:

```powershell
python markdown_to_html.py document.md -s examples/style.css -o site/index.html
```

The CSS is embedded directly into the generated document, so the resulting HTML can be moved or hosted without carrying the stylesheet with it.

## YAML front matter

A Markdown file can begin with YAML metadata:

```markdown
---
title: My Documentation
description: A generated documentation page.
---

# My Documentation

This content will become HTML.
```

The `title` field becomes the HTML `<title>`. The `description` field becomes a description meta tag.

## Live preview

```powershell
python markdown_to_html.py document.md -s examples/style.css --watch
```

This:

1. Builds the initial HTML.
2. Starts a local HTTP server.
3. Opens the generated page in your browser.
4. Watches the Markdown and CSS files.
5. Rebuilds the HTML when they change.

Use a different port when necessary:

```powershell
python markdown_to_html.py document.md --watch --port 8080
```

Prevent automatic browser opening:

```powershell
python markdown_to_html.py document.md --watch --no-browser
```

Press `Ctrl+C` to stop the preview.

## Testing

Install the dependencies and run:

```powershell
python -m unittest discover -s tests -v
```

## Project structure

```text
markdown-to-html/
├── .github/
│   └── workflows/
│       └── tests.yml
├── examples/
│   ├── example.md
│   └── style.css
├── tests/
│   └── test_converter.py
├── .gitignore
├── CONTRIBUTING.md
├── LICENSE.md
├── README.md
├── markdown_to_html.py
└── requirements.txt
```

## Design

The converter deliberately keeps the architecture small:

```text
Markdown file
     │
     ├── YAML front matter
     │
     ▼
Markdown parser
     │
     ▼
HTML body
     │
     ├── optional CSS
     │
     ▼
Complete HTML document
```

The watch mode is an additional layer around the same conversion function, so normal conversion and live preview use the same rendering path.

## License

MIT. See [LICENSE.md](LICENSE.md).
