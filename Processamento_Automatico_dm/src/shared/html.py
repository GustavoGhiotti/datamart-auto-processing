from __future__ import annotations

import html


def sanitize_html_text(value: object, limit: int = 400) -> str:
    text = str(value)
    return html.escape(text, quote=False)[:limit]

