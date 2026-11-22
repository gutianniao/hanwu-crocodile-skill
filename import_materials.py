"""Build a personal research index from explicitly supplied local files."""
import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
from contextlib import closing
from html.parser import HTMLParser
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlparse
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from library import add_document, add_public_sources, has_fts, initialize, personal_index

FORMATS = {".pdf", ".docx", ".pptx", ".xlsx", ".epub", ".txt", ".md", ".csv", ".tsv", ".html", ".htm", ".jsonl"}
LOCAL = "个人导入"
PACKAGE = Path(__file__).resolve().parents[1]


class HTMLText(HTMLParser):
    blocks = {"article", "section", "div", "p", "br", "li", "tr", "h1", "h2", "h3"}
    hidden = {"script", "style", "head", "noscript"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden_tags = []

    def handle_starttag(self, tag, attrs):
        if tag in self.hidden:
            self.hidden_tags.append(tag)
        elif tag in self.blocks and not self.hidden_tags:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if self.hidden_tags and tag == self.hidden_tags[-1]:
            self.hidden_tags.pop()
        elif tag in self.blocks and not self.hidden_tags:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden_tags:
            self.parts.append(data)


def decode(data):
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            return data.decode(encoding)
        except UnicodeError:
            pass
    raise ValueError("文本编码需为 UTF-8 或 GB18030")


def extract_html(data):
    parser = HTMLText()
    parser.feed(decode(data))
    parser.close()
    return "\n".join(line.strip() for line in "".join(parser.parts).splitlines() if line.strip())


def xml_paragraphs(data):
    root = ElementTree.fromstring(data)
    for node in root.iter():
        if node.tag.rsplit("}", 1)[-1] == "p":
            line = "".join(child.text or "" for child in node.iter() if child.tag.rsplit("}", 1)[-1] == "t")
            if line.strip():
                yield line


def pdf_sections(path, args):
    try:
        import pymupdf
    except ImportError as error:
        raise ValueError("读取 PDF 需要安装 pymupdf") from error
    missing = []
    with pymupdf.open(path) as pdf:
        for page in pdf:
            text = page.get_text(sort=True)
            location = f"PDF p.{page.number + 1}"
            if len(re.sub(r"\s", "", text)) < 30:
                missing.append(page.number + 1)
                if args.ocr:
                    ocr = page.get_textpage_ocr(language=args.ocr_language, dpi=200, full=True, tessdata=args.tessdata)
                    scanned = page.get_text(textpage=ocr, sort=True)
                    if len(scanned.strip()) > len(text.strip()):
                        text, location = scanned, location + "（OCR）"
            if text.strip():
                yield location, text
    if missing and not args.ocr:
        print(f"{path.name}：{len(missing)} 页文字很少，可按需用 --ocr 或回看原页。", file=sys.stderr)


def spreadsheet_sections(path):
    try:
        import openpyxl
    except ImportError as error:
        raise ValueError("读取 XLSX 需要安装 openpyxl") from error
    book = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        for sheet in book:
            batch = []
            for row_num, row in enumerate(sheet.values, 1):
                line = "\t".join(str(value) if value is not None else "" for value in row).rstrip()
                if line:
                    batch.append((row_num, line))
                if len(batch) == 25:
                    yield f"工作表 {sheet.title} 第 {batch[0][0]}–{batch[-1][0]} 行", "\n".join(line for _, line in batch)
                    batch = []
            if batch:
                yield f"工作表 {sheet.title} 第 {batch[0][0]}–{batch[-1][0]} 行", "\n".join(line for _, line in batch)
    finally:
        book.close()


def sections(path, args):
    ext = path.suffix.casefold()
    if ext == ".pdf":
        yield from pdf_sections(path, args)
    elif ext == ".xlsx":
        yield from spreadsheet_sections(path)
    elif ext in {".docx", ".pptx", ".epub"}:
        with ZipFile(path) as archive:
            if ext == ".docx":
                yield "Word 正文", "\n".join(xml_paragraphs(archive.read("word/document.xml")))
            elif ext == ".pptx":
                slides = [(int(match[1]), name) for name in archive.namelist() if (match := re.fullmatch(r"ppt/slides/slide(\d+)\.xml", name))]
                for number, name in sorted(slides):
                    yield f"幻灯片 {number}", "\n".join(xml_paragraphs(archive.read(name)))
            else:
                for name in archive.namelist():
                    if name.casefold().endswith((".html", ".xhtml", ".htm")):
                        yield name, extract_html(archive.read(name))
    else:
        data = path.read_bytes()
        yield "本地正文", extract_html(data) if ext in {".html", ".htm"} else decode(data)


def records(path, args):
    if path.suffix.casefold() != ".jsonl":
        yield path.stem, str(path), "", LOCAL, "作者及材料类型待核", sections(path, args)
        return
    with path.open(encoding="utf-8-sig") as file:
        for number, line in enumerate(file, 1):
            if not line.strip():
                continue
            item = json.loads(line)
            if not isinstance(item, dict) or any(not isinstance(item.get(key), str) or not item[key].strip() for key in ("title", "text")):
                raise ValueError(f"JSONL 第 {number} 行需要非空字符串 title 和 text")
            metadata = [item.get(k, "") for k in ("url", "date", "channel", "author")]
            if any(not isinstance(value, str) for value in metadata):
                raise ValueError(f"JSONL 第 {number} 行的 url、date、channel、author 应为字符串")
            url, date, channel, author = metadata
            link = urlparse(url)
            locator = url if link.scheme in ("http", "https") and link.netloc else f"{path} (行 {number})"
            attribution = f"导入记录署名：{author}，按原文核验" if author.strip() else "作者待核"
            yield item["title"].strip(), locator, date, channel or LOCAL, attribution, [(f"导入记录 · 行 {number}", item["text"])]


def build(db, paths, args):
    initialize(db)
    add_public_sources(db)
    seen = set()
    indexed = failed = 0
    use_fts = has_fts(db)
    for path in sorted(paths):
        db.execute("SAVEPOINT material")
        imported = 0
        try:
            checksum = hashlib.sha256()
            with path.open("rb") as file:
                for block in iter(lambda: file.read(1024 * 1024), b""):
                    checksum.update(block)
            digest = checksum.hexdigest()
            if digest not in seen:
                for number, (title, locator, date, channel, attribution, passages) in enumerate(records(path, args), 1):
                    passage_list = [(place, text) for place, text in passages if text.strip()]
                    if not passage_list:
                        continue
                    record = dict(source=f"P{digest[:20].upper()}-{number}", title=title, date=date, locator=locator,
                                  channels=channel, kind="personal", attribution=attribution, status="个人索引")
                    add_document(db, record, passage_list, use_fts)
                    imported += 1
                if imported:
                    seen.add(digest)
                else:
                    raise ValueError("未提取到正文，可能需要 OCR 或转换格式")
        except (OSError, ValueError, RuntimeError, ImportError, KeyError, BadZipFile, ElementTree.ParseError, sqlite3.Error) as error:
            db.execute("ROLLBACK TO material")
            print(f"{path.name}：{error}", file=sys.stderr)
            failed += 1
        else:
            indexed += imported
        finally:
            db.execute("RELEASE material")
    return indexed, failed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", type=Path, nargs="+", help="Files or directories to index recursively.")
    parser.add_argument("--db", type=Path, default=personal_index(), help="Personal index location outside the skill.")
    parser.add_argument("--ocr", action="store_true", help="Use local Tesseract for PDF pages with little text.")
    parser.add_argument("--ocr-language", default="chi_sim+eng")
    parser.add_argument("--tessdata", help="Directory containing OCR language data.")
    args = parser.parse_args()
    destination = args.db.expanduser().resolve()
    if destination.is_relative_to(PACKAGE):
        parser.error("个人索引须保存在 Skill 文件夹以外，以便单独共享 Skill。")
    paths = set()
    for root in args.inputs:
        source = root.expanduser().resolve()
        if not source.exists():
            parser.error(f"输入不存在：{source}")
        files = source.rglob("*") if source.is_dir() else (source,)
        for file in files:
            if file.is_file() and file.suffix.casefold() in FORMATS:
                paths.add(file.resolve())
            elif file.is_file() and (file.suffix.casefold() == ".doc" or file == source):
                print(f"跳过 {file.name}，请转换成受支持的格式。", file=sys.stderr)
    if not paths:
        parser.error("没有受支持的资料。")
    if destination in paths:
        parser.error("索引路径不能覆盖输入资料。")
    if destination.exists():
        try:
            with closing(sqlite3.connect(destination.as_uri() + "?mode=ro", uri=True)) as existing:
                if existing.execute("PRAGMA application_id").fetchone()[0] != 1212372823:
                    parser.error("目的地已有其他文件，请指定新的 --db 路径。")
        except sqlite3.Error:
            parser.error("目的地已有其他文件，请指定新的 --db 路径。")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=destination.parent, suffix=".sqlite3", delete=False) as file:
        temporary = Path(file.name)
    try:
        with closing(sqlite3.connect(temporary)) as db:
            db.execute("PRAGMA application_id=1212372823")
            indexed, failed = build(db, paths, args)
            if not indexed:
                parser.error("未导入任何个人正文，原索引仍可使用。")
            db.commit()
            if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise RuntimeError("个人索引完整性检查失败")
        try:
            os.replace(temporary, destination)
        except PermissionError:
            parser.error("无法替换个人索引。请确认目录可写，并在索引没有被其他程序使用时重试。")
    finally:
        temporary.unlink(missing_ok=True)
    print(f"已收录 {indexed} 条个人资料，{failed} 个输入未导入。索引：{destination}")


if __name__ == "__main__":
    main()
