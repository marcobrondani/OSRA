"""Rendering a report's document model as Markdown, self-contained HTML and
DOCX (FR-67, TR-68a, TR-68b).

The model is plain data: a title, a list of metadata pairs, and blocks of
type ``heading``, ``paragraph``, ``notice``, ``list`` and ``table``. All three
renderers take the same model, so the three formats carry the same content.
Every renderer escapes assessment content (TR-86). None uses colour as the
only signal, and none reads the clock: the same model always renders to the
same bytes.
"""

from __future__ import annotations

import html
import io
import re
import zipfile
from typing import Any
from xml.sax.saxutils import escape as xml_escape

# -- Markdown ---------------------------------------------------------------

_MD_SPECIAL = re.compile(r"([\\`*_{}\[\]<>#|])")


def _md(text: Any) -> str:
    return _MD_SPECIAL.sub(r"\\\1", " ".join(str(text).split()))


def markdown(doc: dict[str, Any]) -> str:
    out = [f"# {_md(doc['title'])}", ""]
    if doc.get("subtitle"):
        out += [_md(doc["subtitle"]), ""]
    if doc.get("meta"):
        out += ["| | |", "|---|---|"] + [f"| {_md(k)} | {_md(v)} |" for k, v in doc["meta"]] + [""]
    for block in doc["blocks"]:
        kind = block["type"]
        if kind == "heading":
            out += ["#" * (block["level"] + 1) + " " + _md(block["text"]), ""]
        elif kind == "paragraph":
            out += [_md(block["text"]), ""]
        elif kind == "notice":
            out += [f"> **{_md(block.get('label', 'Note'))}:** {_md(block['text'])}", ""]
        elif kind == "list":
            out += [f"- {_md(item)}" for item in block["items"]] + [""]
        elif kind == "table":
            if block.get("caption"):
                out += [f"*{_md(block['caption'])}*", ""]
            out.append("| " + " | ".join(_md(c) for c in block["columns"]) + " |")
            out.append("|" + "---|" * len(block["columns"]))
            out += ["| " + " | ".join(_md(c) for c in row) + " |" for row in block["rows"]]
            if not block["rows"]:
                out.append("| " + " | ".join(["—"] * len(block["columns"])) + " |")
            out.append("")
    return "\n".join(out).rstrip("\n") + "\n"


# -- HTML -------------------------------------------------------------------

_CSS = """
:root { --fg: #1b1f24; --muted: #57606a; --line: #d0d7de; --bg: #ffffff; --panel: #f6f8fa; }
@media (prefers-color-scheme: dark) { :root { --fg: #e6edf3; --muted: #9da7b3; --line: #3d444d; --bg: #0d1117; --panel: #161b22; } }
* { box-sizing: border-box; }
body { margin: 0 auto; max-width: 72rem; padding: 2rem 1rem; font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; color: var(--fg); background: var(--bg); }
h1 { font-size: 1.7rem; margin: 0 0 .25rem; } h2 { font-size: 1.3rem; margin-top: 2rem; border-bottom: 1px solid var(--line); padding-bottom: .25rem; }
h3 { font-size: 1.1rem; margin-top: 1.5rem; } h4 { font-size: 1rem; }
.subtitle { color: var(--muted); margin: 0 0 1rem; }
table { border-collapse: collapse; width: 100%; margin: .75rem 0 1.25rem; font-size: .92rem; }
th, td { border: 1px solid var(--line); padding: .35rem .5rem; text-align: left; vertical-align: top; }
th { background: var(--panel); font-weight: 600; }
caption { text-align: left; color: var(--muted); padding-bottom: .25rem; }
.meta th { width: 16rem; }
.notice { border: 1px solid var(--line); border-left: .35rem solid var(--muted); background: var(--panel); padding: .6rem .8rem; margin: 1rem 0; }
.notice strong { display: block; }
@media print { body { max-width: none; } }
""".strip()


def _h(text: Any) -> str:
    return html.escape(str(text), quote=True)


def html_document(doc: dict[str, Any]) -> str:
    out = ["<!doctype html>", '<html lang="en-GB">', "<head>", '<meta charset="utf-8">',
           '<meta name="viewport" content="width=device-width, initial-scale=1">',
           f"<title>{_h(doc['title'])}</title>", f"<style>\n{_CSS}\n</style>", "</head>", "<body>", "<main>",
           f"<h1>{_h(doc['title'])}</h1>"]
    if doc.get("subtitle"):
        out.append(f'<p class="subtitle">{_h(doc["subtitle"])}</p>')
    if doc.get("meta"):
        out.append('<table class="meta"><tbody>')
        out += [f'<tr><th scope="row">{_h(k)}</th><td>{_h(v)}</td></tr>' for k, v in doc["meta"]]
        out.append("</tbody></table>")
    for block in doc["blocks"]:
        kind = block["type"]
        if kind == "heading":
            level = min(block["level"] + 1, 6)
            out.append(f"<h{level}>{_h(block['text'])}</h{level}>")
        elif kind == "paragraph":
            out.append(f"<p>{_h(block['text'])}</p>")
        elif kind == "notice":
            out.append(f'<div class="notice" role="note"><strong>{_h(block.get("label", "Note"))}:</strong> {_h(block["text"])}</div>')
        elif kind == "list":
            out.append("<ul>" + "".join(f"<li>{_h(item)}</li>" for item in block["items"]) + "</ul>")
        elif kind == "table":
            out.append("<table>")
            if block.get("caption"):
                out.append(f"<caption>{_h(block['caption'])}</caption>")
            out.append("<thead><tr>" + "".join(f'<th scope="col">{_h(c)}</th>' for c in block["columns"]) + "</tr></thead>")
            out.append("<tbody>")
            rows = block["rows"] or [["—"] * len(block["columns"])]
            out += ["<tr>" + "".join(f"<td>{_h(c)}</td>" for c in row) + "</tr>" for row in rows]
            out.append("</tbody></table>")
    out += ["</main>", "</body>", "</html>"]
    return "\n".join(out) + "\n"


# -- DOCX -------------------------------------------------------------------

_INVALID_XML = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f]")
_FIXED_TIME = (1980, 1, 1, 0, 0, 0)

_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/><Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/></Types>"""
_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/></Relationships>"""
_DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>"""
_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_STYLES = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="{_W}"><w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/><w:sz w:val="21"/><w:lang w:val="en-GB"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="264" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:after="80"/></w:pPr><w:rPr><w:b/><w:sz w:val="40"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Subtitle"><w:name w:val="Subtitle"/><w:basedOn w:val="Normal"/><w:rPr><w:i/><w:color w:val="57606A"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:before="360" w:after="120"/><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:sz w:val="30"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:before="240" w:after="80"/><w:outlineLvl w:val="1"/></w:pPr><w:rPr><w:b/><w:sz w:val="25"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:outlineLvl w:val="2"/></w:pPr><w:rPr><w:b/><w:sz w:val="22"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Notice"><w:name w:val="Notice"/><w:basedOn w:val="Normal"/><w:pPr><w:pBdr><w:left w:val="single" w:sz="18" w:space="8" w:color="57606A"/></w:pBdr><w:ind w:left="240"/></w:pPr></w:style>
<w:style w:type="table" w:styleId="TableGrid"><w:name w:val="Table Grid"/><w:tblPr><w:tblBorders><w:top w:val="single" w:sz="4" w:color="999999"/><w:left w:val="single" w:sz="4" w:color="999999"/><w:bottom w:val="single" w:sz="4" w:color="999999"/><w:right w:val="single" w:sz="4" w:color="999999"/><w:insideH w:val="single" w:sz="4" w:color="999999"/><w:insideV w:val="single" w:sz="4" w:color="999999"/></w:tblBorders><w:tblCellMar><w:left w:w="80" w:type="dxa"/><w:right w:w="80" w:type="dxa"/></w:tblCellMar></w:tblPr></w:style>
</w:styles>"""


def _x(text: Any) -> str:
    return xml_escape(_INVALID_XML.sub("", str(text)))


def _para(text: Any, style: str | None = None, bold: bool = False, prefix: str = "") -> str:
    ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    rpr = "<w:rPr><w:b/></w:rPr>" if bold else ""
    return f'<w:p>{ppr}<w:r>{rpr}<w:t xml:space="preserve">{_x(prefix)}{_x(text)}</w:t></w:r></w:p>'


def _table(columns: list, rows: list, caption: str | None = None) -> str:
    out = []
    if caption:
        out.append(_para(caption, "Subtitle"))
    width = 9638 // max(len(columns), 1)  # A4 text width in twentieths of a point, shared equally
    grid = "".join(f'<w:gridCol w:w="{width}"/>' for _ in columns)
    out.append('<w:tbl><w:tblPr><w:tblStyle w:val="TableGrid"/><w:tblW w:w="5000" w:type="pct"/></w:tblPr>'
               f"<w:tblGrid>{grid}</w:tblGrid>")
    out.append('<w:tr><w:trPr><w:tblHeader/></w:trPr>'
               + "".join(f"<w:tc>{_para(c, bold=True)}</w:tc>" for c in columns) + "</w:tr>")
    for row in rows or [["—"] * len(columns)]:
        out.append("<w:tr>" + "".join(f"<w:tc>{_para(c)}</w:tc>" for c in row) + "</w:tr>")
    out.append("</w:tbl>")
    out.append(_para(""))
    return "".join(out)


def docx(doc: dict[str, Any]) -> bytes:
    body = [_para(doc["title"], "Title")]
    if doc.get("subtitle"):
        body.append(_para(doc["subtitle"], "Subtitle"))
    if doc.get("meta"):
        body.append(_table(["", ""], [[k, v] for k, v in doc["meta"]]))
    for block in doc["blocks"]:
        kind = block["type"]
        if kind == "heading":
            body.append(_para(block["text"], f"Heading{min(block['level'], 3)}"))
        elif kind == "paragraph":
            body.append(_para(block["text"]))
        elif kind == "notice":
            body.append(_para(block["text"], "Notice", prefix=f"{block.get('label', 'Note')}: "))
        elif kind == "list":
            body += [_para(item, prefix="• ") for item in block["items"]]
        elif kind == "table":
            body.append(_table(block["columns"], block["rows"], block.get("caption")))
    document = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:document xmlns:w="{_W}"><w:body>'
                + "".join(body)
                + '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1134" w:right="1134" w:bottom="1134" '
                  'w:left="1134" w:header="567" w:footer="567" w:gutter="0"/></w:sectPr></w:body></w:document>')
    core = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/">'
            f"<dc:title>{_x(doc['title'])}</dc:title><dc:creator>OSRA-CODE</dc:creator></cp:coreProperties>")
    parts = [
        ("[Content_Types].xml", _CONTENT_TYPES),
        ("_rels/.rels", _RELS),
        ("docProps/core.xml", core),
        ("word/_rels/document.xml.rels", _DOC_RELS),
        ("word/document.xml", document),
        ("word/styles.xml", _STYLES),
    ]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, text in parts:
            info = zipfile.ZipInfo(name, date_time=_FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, text.encode("utf-8"))
    return buffer.getvalue()


RENDERERS = {
    "md": lambda doc: markdown(doc).encode("utf-8"),
    "html": lambda doc: html_document(doc).encode("utf-8"),
    "docx": docx,
}
