import re
from typing import NamedTuple

class BlockData(NamedTuple):
    text: str
    font_size: float
    font_weight: int
    font_italic: bool
    color: str

_HEADING_RE = re.compile(r'^(#{1,6})\s+(.*)$')
_INLINE_RE = re.compile(r'(\*\*.+?\*\*|__.+?__|\*.+?\*|_.+?_|`.+?`)')
_HEADING_SIZE = {1: 28.0, 2: 24.0, 3: 20.0, 4: 18.0, 5: 16.0, 6: 14.0}
_HEADING_COLOR = "#ffffff"
_BODY_COLOR = "#ffffff"
_CODE_COLOR = "#d4d4d4"


def _parse_inline(text: str) -> list[dict]:
    runs = []
    pos = 0
    for match in _INLINE_RE.finditer(text):
        if match.start() > pos:
            runs.append({"text": text[pos:match.start()], "bold": False, "italic": False, "code": False})
        token = match.group(0)
        if token.startswith("**") or token.startswith("__"):
            runs.append({"text": token[2:-2], "bold": True,  "italic": False, "code": False})
        elif token.startswith("`"):
            runs.append({"text": token[1:-1], "bold": False, "italic": False, "code": True})
        else:
            runs.append({"text": token[1:-1], "bold": False, "italic": True,  "code": False})
        pos = match.end()
    if pos < len(text):
        runs.append({"text": text[pos:], "bold": False, "italic": False, "code": False})
    return runs


def markdown_to_text_blocks(markdown: str) -> list[dict]:
    if not markdown:
        return []

    markdown = re.sub(r'<[^>]+>', '', markdown)

    blocks: list[dict] = []
    pending: list[str] = []

    def flush_paragraph() -> None:
        if not pending:
            return
        joined = "\n".join(pending).strip()
        pending.clear()
        if not joined:
            return
        for run in _parse_inline(joined):
            if not run["text"]:
                continue
            blocks.append(BlockData(
                text=run["text"],
                font_size=16.0,
                font_weight=700 if run["bold"] else 400,
                font_italic=run["italic"],
                color=_CODE_COLOR if run["code"] else _BODY_COLOR,
            ))

    for line in markdown.splitlines():
        m = _HEADING_RE.match(line)
        if m:
            flush_paragraph()
            level = len(m.group(1))
            blocks.append(BlockData(
                text=m.group(2).strip(),
                font_size=_HEADING_SIZE.get(level, 16.0),
                font_weight=700,
                font_italic=False,
                color=_HEADING_COLOR,
            ))
        else:
            pending.append(line)

    flush_paragraph()
    return blocks