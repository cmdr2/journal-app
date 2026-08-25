import re
import uuid


class MarkdownToHtmlConverter:
    def __init__(self):
        # Updated regex patterns to handle code blocks properly, including '+' in language names
        self.code_block_pattern = re.compile(r"```([\w+]+)?\n(.*?)```", re.DOTALL)
        self.inline_code_pattern = re.compile(r"`([^`]+)`")
        self.header_pattern = re.compile(r"^(#{1,6})\s+(.+)", re.MULTILINE)
        self.bold_pattern = re.compile(r"\*\*(.+?)\*\*")
        self.italic_pattern = re.compile(r"\*(.+?)\*")
        self.strikethrough_pattern = re.compile(r"\~\~(.+?)\~\~")
        self.link_pattern = re.compile(r"\[(.+?)\]\((.+?)\)")
        self.image_pattern = re.compile(r"!\[(.*?)\]\((.+?)\)")
        self.ul_list_pattern = re.compile(r"^[-*]\s+(.+)", re.MULTILINE)
        self.ol_list_pattern = re.compile(r"^\d+\.\s+(.+)", re.MULTILINE)
        self.table_pattern = re.compile(r"^\|(.+?)\|\n\|(?:\s*:?-+:?\s*\|)+\n((?:\|.+?\|\n)+)", re.MULTILINE)
        self.code_blocks = {}
        self.tables = {}

    def convert(self, markdown: str) -> str:
        html = markdown

        # Extract code blocks and replace them with placeholders
        html = self.code_block_pattern.sub(self._extract_code_block, html)

        # Extract inline code and replace with placeholders
        html = self.inline_code_pattern.sub(self._extract_inline_code, html)

        # Extract tables and replace with placeholders (must happen BEFORE
        # inline formatting so that generated tags like <strong> inside
        # cells aren't escaped later)
        html = self.table_pattern.sub(self._extract_table, html)

        # Process headers
        html = self.header_pattern.sub(self._replace_header, html)

        # Handle bold text
        html = self.bold_pattern.sub(r"<strong>\1</strong>", html)

        # Handle italic text
        html = self.italic_pattern.sub(r"<em>\1</em>", html)

        # Handle strikethrough text
        html = self.strikethrough_pattern.sub(r"<del>\1</del>", html)

        # Handle images
        html = self.image_pattern.sub(r'<img src="\2" alt="\1" />', html)

        # Handle links
        html = self.link_pattern.sub(r'<a href="\2">\1</a>', html)

        # Handle unordered lists
        html = self._replace_unordered_lists(html)

        # Handle ordered lists
        html = self._replace_ordered_lists(html)


        # Wrap paragraphs around text blocks
        html = self._wrap_paragraphs(html)

        # Replace GUID placeholders with actual code block contents
        for guid, content in self.code_blocks.items():
            if isinstance(content, tuple):
                # It's a code block with (language, code)
                language, code = content
                html = html.replace(guid, self._wrap_code_block(language, code))
            else:
                # It's inline code
                html = html.replace(guid, f"<code>{self._escape_html(content)}</code>")

        # Replace table placeholders with rendered tables (after code
        # placeholders are restored so inline code inside cells works)
        for guid, raw_table in self.tables.items():
            for cguid, content in self.code_blocks.items():
                if isinstance(content, tuple):
                    language, code = content
                    raw_table = raw_table.replace(cguid, self._wrap_code_block(language, code))
                else:
                    raw_table = raw_table.replace(cguid, f"<code>{self._escape_html(content)}</code>")
            html = html.replace(guid, self._render_table(raw_table))

        return html

    def _extract_table(self, match):
        guid = str(uuid.uuid4())
        self.tables[guid] = match.group(0)
        return guid

    def _extract_code_block(self, match):
        language = match.group(1) if match.group(1) else "plaintext"
        code = match.group(2)

        # Generate a GUID placeholder
        guid = str(uuid.uuid4())
        self.code_blocks[guid] = (language, code)  # Store the language and code block

        return guid  # Return the placeholder

    def _extract_inline_code(self, match):
        code = match.group(1)

        # Generate a GUID placeholder
        guid = str(uuid.uuid4())
        self.code_blocks[guid] = code  # Store just the code content

        return guid  # Return the placeholder

    def _wrap_code_block(self, language: str, code: str) -> str:
        # Escape HTML characters in the code
        escaped_code = self._escape_html(code)
        return f'<pre><code class="codeblock language-{language}">{escaped_code}</code></pre>'

    def _replace_header(self, match):
        return f'<b style="display: block" class="header">{match.group(0)}</b>'

    def _replace_lists(self, text: str, ordered: bool) -> str:
        lines = text.split("\n")
        result = []
        stack = []  # stack of (indent, start_index or None)

        for line in lines:
            if ordered:
                match = re.match(r"^(\s*)(\d+)\.\s+(.+)", line)
            else:
                match = re.match(r"^(\s*)[-*]\s+(.+)", line)

            if match:
                indent = len(match.group(1))

                if ordered:
                    number = int(match.group(2))
                    content = match.group(3)
                else:
                    number = None
                    content = match.group(2)

                # Open new levels
                while not stack or indent > stack[-1][0]:
                    if ordered:
                        start_attr = f' start="{number}"' if number != 1 else ""
                        result.append(f"<ol{start_attr}>")
                        stack.append((indent, number))
                    else:
                        result.append("<ul>")
                        stack.append((indent, None))

                # Close levels
                while stack and indent < stack[-1][0]:
                    tag = "ol" if ordered else "ul"
                    result.append(f"</{tag}>")
                    stack.pop()

                result.append(f"<li>{content}</li>")
            else:
                # Close all open lists
                while stack:
                    tag = "ol" if ordered else "ul"
                    result.append(f"</{tag}>")
                    stack.pop()
                result.append(line)

        # Close any remaining lists
        while stack:
            tag = "ol" if ordered else "ul"
            result.append(f"</{tag}>")
            stack.pop()

        return "\n".join(result)

    def _replace_unordered_lists(self, text: str) -> str:
        return self._replace_lists(text, ordered=False)

    def _replace_ordered_lists(self, text: str) -> str:
        return self._replace_lists(text, ordered=True)

    def _render_table(self, raw_table: str) -> str:
        lines = raw_table.split("\n")
        headers = [h.strip() for h in lines[0].strip().strip("|").split("|")]
        rows = [line for line in lines[2:] if line.strip()]

        thead = "<thead><tr>" + "".join(f"<th>{self._format_inline(h)}</th>" for h in headers) + "</tr></thead>"
        tbody = "<tbody>"
        for row in rows:
            columns = [c.strip() for c in row.strip().strip("|").split("|")]
            tbody += "<tr>" + "".join(f"<td>{self._format_inline(c)}</td>" for c in columns) + "</tr>"
        tbody += "</tbody>"

        return f"<table>{thead}{tbody}</table>"

    def _format_inline(self, text: str) -> str:
        # Apply the same inline formatting rules used elsewhere in the
        # document. Code-block/inline-code placeholders have already been
        # substituted back by this point.
        text = self.bold_pattern.sub(r"<strong>\1</strong>", text)
        text = self.italic_pattern.sub(r"<em>\1</em>", text)
        text = self.strikethrough_pattern.sub(r"<del>\1</del>", text)
        text = self.image_pattern.sub(r'<img src="\2" alt="\1" />', text)
        text = self.link_pattern.sub(r'<a href="\2">\1</a>', text)
        return text

    def _wrap_paragraphs(self, html: str) -> str:
        lines = html.split("\n")
        inside_paragraph = False
        result = []
        for line in lines:
            if not line.strip():
                if inside_paragraph:
                    result.append("</p>")
                    inside_paragraph = False
            else:
                if not inside_paragraph:
                    result.append("<p>")
                    inside_paragraph = True
                result.append(line)
        if inside_paragraph:
            result.append("</p>")
        return "\n".join(result)

    def _escape_html(self, text: str) -> str:
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )
