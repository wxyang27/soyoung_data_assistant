import argparse
import html
import re
import sys
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree as ET


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "knowledge" / "raw"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in {"script", "style"}:
            self.skip_depth += 1

    def handle_endtag(self, tag):
        if tag.lower() in {"script", "style"} and self.skip_depth:
            self.skip_depth -= 1

    def handle_data(self, data):
        if self.skip_depth:
            return
        text = data.strip()
        if text:
            self.parts.append(text)

    def text(self):
        return "\n".join(self.parts)


def normalize_text(text: str) -> str:
    text = html.unescape(text)
    text = text.replace("\u3000", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(errors="ignore")


def extract_html(path: Path) -> str:
    parser = TextExtractor()
    parser.feed(read_text(path))
    return parser.text()


def extract_docx(path: Path) -> str:
    with zipfile.ZipFile(path) as zf:
        xml = zf.read("word/document.xml")

    root = ET.fromstring(xml)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs = []
    for paragraph in root.findall(".//w:p", ns):
        runs = [node.text or "" for node in paragraph.findall(".//w:t", ns)]
        text = "".join(runs).strip()
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs)


def extract_xlsx(path: Path) -> str:
    ns = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(path) as zf:
        shared_strings = []
        if "xl/sharedStrings.xml" in zf.namelist():
            root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in root.findall("main:si", ns):
                texts = [node.text or "" for node in si.findall(".//main:t", ns)]
                shared_strings.append("".join(texts))

        workbook = ET.fromstring(zf.read("xl/workbook.xml"))
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        rel_map = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in rels
            if rel.attrib.get("Target")
        }

        lines = []
        for sheet in workbook.findall(".//main:sheet", ns):
            sheet_name = sheet.attrib.get("name", "sheet")
            rel_id = sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            target = rel_map.get(rel_id)
            if not target:
                continue
            sheet_path = "xl/" + target.lstrip("/")
            if sheet_path not in zf.namelist():
                sheet_path = "xl/worksheets/" + Path(target).name
            if sheet_path not in zf.namelist():
                continue

            lines.append(f"# Sheet: {sheet_name}")
            sheet_root = ET.fromstring(zf.read(sheet_path))
            for row in sheet_root.findall(".//main:row", ns)[:80]:
                cells = []
                for cell in row.findall("main:c", ns):
                    value = cell.find("main:v", ns)
                    if value is None:
                        cells.append("")
                        continue
                    raw_value = value.text or ""
                    if cell.attrib.get("t") == "s":
                        try:
                            cells.append(shared_strings[int(raw_value)])
                        except (ValueError, IndexError):
                            cells.append(raw_value)
                    else:
                        cells.append(raw_value)
                line = " | ".join(item for item in cells if item)
                if line:
                    lines.append(line)
    return "\n".join(lines)


def extract_text(path: Path) -> tuple[str, str]:
    suffix = path.suffix.lower()
    if suffix in {".md", ".txt", ".sql", ".csv"}:
        return normalize_text(read_text(path)), "ok"
    if suffix in {".html", ".htm"}:
        return normalize_text(extract_html(path)), "ok"
    if suffix == ".docx":
        return normalize_text(extract_docx(path)), "ok"
    if suffix == ".xlsx":
        return normalize_text(extract_xlsx(path)), "ok"
    if suffix == ".pdf":
        return "", "needs_pypdf"
    return "", "unsupported"


def estimate_chunks(text: str, chunk_size: int) -> int:
    if not text:
        return 0
    return max(1, (len(text) + chunk_size - 1) // chunk_size)


def preview(text: str, width: int = 120) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text[:width]


def main():
    parser = argparse.ArgumentParser(description="Audit raw knowledge files before ingestion.")
    parser.add_argument("--raw-dir", default=str(RAW_DIR))
    parser.add_argument("--chunk-size", type=int, default=900)
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    if not raw_dir.exists():
        print(f"Raw knowledge directory does not exist: {raw_dir}")
        sys.exit(1)

    rows = []
    for path in sorted(raw_dir.rglob("*")):
        if not path.is_file():
            continue
        try:
            text, status = extract_text(path)
            error = ""
        except Exception as exc:
            text, status, error = "", "error", str(exc)
        rows.append(
            {
                "file": str(path.relative_to(PROJECT_ROOT)),
                "type": path.suffix.lower().lstrip("."),
                "bytes": path.stat().st_size,
                "status": status,
                "chars": len(text),
                "chunks": estimate_chunks(text, args.chunk_size),
                "preview": preview(text),
                "error": error,
            }
        )

    print("| 文件 | 类型 | 大小KB | 状态 | 字符数 | 预估chunk | 预览/错误 |")
    print("|---|---:|---:|---|---:|---:|---|")
    for row in rows:
        detail = row["error"] or row["preview"]
        detail = detail.replace("|", "\\|")
        print(
            f"| {row['file']} | {row['type']} | {row['bytes'] / 1024:.1f} | "
            f"{row['status']} | {row['chars']} | {row['chunks']} | {detail} |"
        )

    ok_count = sum(1 for row in rows if row["status"] == "ok")
    total_chunks = sum(row["chunks"] for row in rows)
    print()
    print(f"Summary: {ok_count}/{len(rows)} files parseable with current environment; estimated chunks={total_chunks}.")


if __name__ == "__main__":
    main()
