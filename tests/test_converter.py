import tempfile
import unittest
from pathlib import Path

from markdown_to_html import MarkdownConverter, build_html, parse_front_matter


class MarkdownConverterTests(unittest.TestCase):
    def test_basic_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "document.md"
            source.write_text("# Hello\n\nThis is **bold**.", encoding="utf-8")

            result = MarkdownConverter.parse_file(source)

            self.assertIn("<h1>Hello</h1>", result)
            self.assertIn("<strong>bold</strong>", result)
            self.assertIn("<title>document</title>", result)

    def test_front_matter(self):
        document = parse_front_matter(
            "---\n"
            "title: Test Page\n"
            "description: A test document.\n"
            "---\n"
            "# Hello\n"
        )

        self.assertEqual(document.metadata["title"], "Test Page")
        self.assertEqual(document.metadata["description"], "A test document.")
        self.assertEqual(document.body, "# Hello\n")

    def test_invalid_front_matter(self):
        with self.assertRaises(ValueError):
            parse_front_matter("---\n: invalid: yaml\n---\n# Test\n")

    def test_css_is_embedded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "document.md"
            style = root / "style.css"
            source.write_text("# Hello\n", encoding="utf-8")
            style.write_text("body { max-width: 800px; }", encoding="utf-8")

            result = MarkdownConverter.parse_file(source, style)

            self.assertIn("<style", result)
            self.assertIn("max-width: 800px", result)

    def test_output_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "document.md"
            output = root / "site" / "index.html"
            source.write_text("# Hello\n", encoding="utf-8")

            result = build_html(source, output)

            self.assertEqual(result, output)
            self.assertTrue(output.exists())
            self.assertIn("<h1>Hello</h1>", output.read_text(encoding="utf-8"))

    def test_title_is_escaped(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "document.md"
            source.write_text("---\ntitle: '<script>alert(1)</script>'\n---\n# Safe\n", encoding="utf-8")

            result = MarkdownConverter.parse_file(source)

            self.assertNotIn("<title><script>", result)
            self.assertIn("&lt;script&gt;", result)


if __name__ == "__main__":
    unittest.main()
