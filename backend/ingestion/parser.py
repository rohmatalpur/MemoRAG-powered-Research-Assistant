from __future__ import annotations
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

import requests

from backend.models import ParsedPaper, ParsedSection, ParsedReference
from backend.config import GROBID_URL


TEI_NS = "http://www.tei-c.org/ns/1.0"


class PaperParser:
    def __init__(self, grobid_url: str = GROBID_URL):
        self.grobid_url = grobid_url.rstrip("/")

    def parse(self, source: str | Path) -> ParsedPaper:
        s = str(source)
        if s.endswith(".pdf"):
            return self._parse_pdf(Path(source))
        elif s.endswith(".docx"):
            return self._parse_docx(Path(source))
        raise ValueError(f"Unsupported source type: {source}. Only PDF and DOCX are supported.")

    # ------------------------------------------------------------------ PDF
    def _parse_pdf(self, path: Path) -> ParsedPaper:
        try:
            return self._parse_with_grobid(path)
        except Exception:
            return self._parse_with_pymupdf(path)

    def _parse_with_grobid(self, path: Path) -> ParsedPaper:
        with open(path, "rb") as f:
            resp = requests.post(
                f"{self.grobid_url}/api/processFulltextDocument",
                files={"input": f},
                data={"consolidateCitations": "0"},
                timeout=120,
            )
        if resp.status_code != 200:
            raise RuntimeError(f"Grobid returned {resp.status_code}")
        return self._from_tei_xml(resp.text, str(path))

    def _from_tei_xml(self, xml: str, source_path: str) -> ParsedPaper:
        root = ET.fromstring(xml)
        ns = {"tei": TEI_NS}

        def tag(name: str) -> str:
            return f"{{{TEI_NS}}}{name}"

        # Header
        header = root.find(f".//{tag('teiHeader')}")
        title = ""
        if header is not None:
            t = header.find(f".//{tag('title')}[@level='a']")
            if t is not None and t.text:
                title = t.text.strip()

        authors: list[str] = []
        for author in root.findall(f".//{tag('author')}"):
            forename = author.find(f".//{tag('forename')}")
            surname = author.find(f".//{tag('surname')}")
            name_parts = []
            if forename is not None and forename.text:
                name_parts.append(forename.text.strip())
            if surname is not None and surname.text:
                name_parts.append(surname.text.strip())
            if name_parts:
                authors.append(" ".join(name_parts))

        year: Optional[int] = None
        date_el = root.find(f".//{tag('date')}[@type='published']")
        if date_el is not None and date_el.get("when"):
            try:
                year = int(date_el.get("when", "")[:4])
            except ValueError:
                pass

        abstract = ""
        abs_el = root.find(f".//{tag('abstract')}")
        if abs_el is not None:
            abstract = " ".join(abs_el.itertext()).strip()

        # Body sections
        sections: list[ParsedSection] = []
        body = root.find(f".//{tag('body')}")
        if body is not None:
            for div in body.findall(f"{tag('div')}"):
                head = div.find(tag("head"))
                heading = head.text.strip() if head is not None and head.text else "Section"
                content = " ".join(div.itertext()).strip()
                if head is not None and head.text:
                    content = content[len(head.text):].strip()
                sections.append(ParsedSection(
                    heading=heading,
                    type=self._infer_section_type(heading),
                    content=content,
                    page_start=0,
                    page_end=0,
                ))

        # Abstract as first section
        if abstract:
            sections.insert(0, ParsedSection(
                heading="Abstract",
                type="abstract",
                content=abstract,
                page_start=0,
                page_end=0,
            ))

        # References
        references: list[ParsedReference] = []
        for bib in root.findall(f".//{tag('biblStruct')}"):
            ref = self._parse_bib_struct(bib, ns)
            if ref:
                references.append(ref)

        return ParsedPaper(
            title=title,
            authors=authors,
            year=year,
            abstract=abstract,
            sections=sections,
            references=references,
            source_path=source_path,
            source_type="pdf",
        )

    def _parse_bib_struct(self, bib, ns) -> Optional[ParsedReference]:
        def tag(name: str) -> str:
            return f"{{{TEI_NS}}}{name}"

        title_el = bib.find(f".//{tag('title')}[@level='a']") or bib.find(f".//{tag('title')}")
        title = (title_el.text or "").strip() if title_el is not None else ""
        if not title:
            return None

        authors: list[str] = []
        for author in bib.findall(f".//{tag('author')}"):
            surname = author.find(f".//{tag('surname')}")
            if surname is not None and surname.text:
                authors.append(surname.text.strip())

        year = None
        date_el = bib.find(f".//{tag('date')}")
        if date_el is not None and date_el.get("when"):
            try:
                year = int(date_el.get("when", "")[:4])
            except ValueError:
                pass

        doi = None
        for idno in bib.findall(f".//{tag('idno')}"):
            if idno.get("type", "").lower() == "doi":
                doi = (idno.text or "").strip()

        return ParsedReference(title=title, authors=authors, year=year, doi=doi)

    def _parse_with_pymupdf(self, path: Path) -> ParsedPaper:
        import fitz  # PyMuPDF
        doc = fitz.open(str(path))
        full_text = ""
        for page in doc:
            full_text += page.get_text()

        sections = [ParsedSection(
            heading="Full Text",
            type="body",
            content=full_text,
            page_start=0,
            page_end=len(doc) - 1,
        )]
        return ParsedPaper(
            title=path.stem,
            sections=sections,
            source_path=str(path),
            source_type="pdf",
        )

    # ------------------------------------------------------------------ DOCX
    def _parse_docx(self, path: Path) -> ParsedPaper:
        from docx import Document
        doc = Document(str(path))

        sections: list[ParsedSection] = []
        current_heading = "Introduction"
        current_paragraphs: list[str] = []

        for para in doc.paragraphs:
            if para.style.name.startswith("Heading"):
                if current_paragraphs:
                    sections.append(ParsedSection(
                        heading=current_heading,
                        type=self._infer_section_type(current_heading),
                        content="\n\n".join(current_paragraphs),
                        page_start=0,
                        page_end=0,
                    ))
                current_heading = para.text.strip() or current_heading
                current_paragraphs = []
            elif para.text.strip():
                current_paragraphs.append(para.text.strip())

        if current_paragraphs:
            sections.append(ParsedSection(
                heading=current_heading,
                type=self._infer_section_type(current_heading),
                content="\n\n".join(current_paragraphs),
                page_start=0,
                page_end=0,
            ))

        title = sections[0].content[:100] if sections else path.stem
        return ParsedPaper(
            title=title,
            sections=sections,
            source_path=str(path),
            source_type="docx",
        )

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _infer_section_type(heading: str) -> str:
        h = heading.lower()
        if "abstract" in h:
            return "abstract"
        if "introduction" in h:
            return "introduction"
        if "related" in h or "background" in h or "prior" in h:
            return "related_work"
        if "method" in h or "approach" in h or "model" in h or "architecture" in h:
            return "methods"
        if "experiment" in h or "evaluat" in h or "result" in h:
            return "experiments"
        if "conclusion" in h or "discussion" in h or "future" in h:
            return "conclusion"
        if "reference" in h or "bibliograph" in h:
            return "references"
        return "body"
