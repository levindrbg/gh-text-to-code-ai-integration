"""
Extract text from all .docx and .pdf in 04_knowledge base and write .txt files.
Run from repo root: python "04_knowledge base/extract_to_txt.py"

- .docx: uses stdlib only (zipfile + xml.etree).
- .pdf: requires pypdf (pip install pypdf). Skips PDFs if not installed.
"""

import os
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

# Namespace for Word XML
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def extract_docx_text(docx_path: Path) -> str:
    """Extract all text from a .docx using stdlib only."""
    parts = []
    try:
        with zipfile.ZipFile(docx_path, "r") as z:
            if "word/document.xml" not in z.namelist():
                return f"[No word/document.xml in {docx_path.name}]"
            with z.open("word/document.xml") as f:
                tree = ET.parse(f)
                root = tree.getroot()
                for elem in root.iter(f"{{{W_NS}}}t"):
                    if elem.text:
                        parts.append(elem.text)
                    if elem.tail:
                        parts.append(elem.tail)
    except Exception as e:
        return f"[Error reading docx: {e}]"
    text = "".join(parts)
    # Normalize whitespace: collapse multiple spaces/newlines, keep paragraph breaks
    lines = []
    for line in text.replace("\r", "\n").split("\n"):
        lines.append(" ".join(line.split()))
    return "\n".join(line for line in lines if line).strip()


def extract_pdf_text(pdf_path: Path) -> str:
    """Extract text from a .pdf using pypdf if available."""
    try:
        from pypdf import PdfReader
    except ImportError:
        return f"[Install pypdf to extract PDFs: pip install pypdf]"
    parts = []
    try:
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            t = page.extract_text()
            if t:
                parts.append(t)
    except Exception as e:
        return f"[Error reading pdf: {e}]"
    return "\n\n".join(parts).strip() if parts else "[No text extracted]"


def main():
    base = Path(__file__).resolve().parent
    if not base.exists():
        print("Base dir not found.", file=sys.stderr)
        sys.exit(1)

    out_dir = base / "extracted_txt"
    out_dir.mkdir(exist_ok=True)

    for root, _dirs, files in os.walk(base):
        root_path = Path(root)
        # Skip our own output and extracted zip folders
        if "extracted_txt" in root_path.parts or "main_extract" in root_path.parts or root_path.name.endswith("_extract"):
            continue
        for name in files:
            if name.startswith(".") or name == "extract_to_txt.py":
                continue
            path = root_path / name
            rel = path.relative_to(base)
            out_name = rel.with_suffix(".txt").name
            # Keep subfolder structure in extracted_txt
            out_sub = out_dir / rel.parent
            out_sub.mkdir(parents=True, exist_ok=True)
            out_path = out_sub / out_name

            if path.suffix.lower() == ".docx":
                text = extract_docx_text(path)
                out_path.write_text(text, encoding="utf-8")
                print("DOCX:", rel)
            elif path.suffix.lower() == ".pdf":
                text = extract_pdf_text(path)
                out_path.write_text(text, encoding="utf-8")
                print("PDF:", rel)
            else:
                continue

    print("Done. Text files in:", out_dir)


if __name__ == "__main__":
    main()
