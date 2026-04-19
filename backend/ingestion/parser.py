from __future__ import annotations
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

import requests
import trafilatura

from backend.models import ParsedPaper, ParsedSection, ParsedReference
from backend.config import GROBID_URL


TEI_NS = "http://www.tei-c.org/ns/1.0"


class PaperParser:
    def __init__(self, grobid_url: str = GROBID_URL):
        self.grobid_url = grobid_url.rstrip("/")

    def parse(self, source: str | Path) -> ParsedPaper:
        s = str(source)
        if s.startswith("http://") or s.startswith("https://"):
            return self._parse_web(s)
        elif s.endswith(".pdf"):
            return self._parse_pdf(Path(source))
        elif s.endswith(".docx"):
            return self._parse_docx(Path(source))
        raise ValueError(f"Unsupported source: {source}")

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

    # ------------------------------------------------------------------ URL
    def _parse_web(self, url: str) -> ParsedPaper:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            raise RuntimeError(f"Could not fetch URL: {url}")

        metadata = trafilatura.extract_metadata(downloaded)
        title = metadata.title if metadata and metadata.title else url
        authors = [metadata.author] if metadata and metadata.author else []
        year = None
        if metadata and metadata.date:
            try:
                year = int(str(metadata.date)[:4])
            except ValueError:
                pass

        sections = self._extract_sections_from_html(downloaded)
        if not sections:
            # Fallback: trafilatura plain-text extraction as one blob
            text = trafilatura.extract(
                downloaded, include_tables=False, include_comments=False
            ) or ""
            sections = [ParsedSection(
                heading="Full Text", type="body",
                content=text, page_start=0, page_end=0,
            )]

        references = self._extract_web_references(downloaded, base_url=url)

        return ParsedPaper(
            title=title,
            authors=authors,
            year=year,
            sections=sections,
            references=references,
            source_path=url,
            source_type="url",
        )

    def _extract_sections_from_html(self, html: str) -> list[ParsedSection]:
        """
        Walk HTML headings (h1-h4) and group content between them into
        ParsedSection objects, preserving the structure of the page.
        """
        from bs4 import BeautifulSoup, NavigableString, Tag

        soup = BeautifulSoup(html, "lxml")

        # Remove noise elements
        for tag in soup(["script", "style", "nav", "footer", "header",
                         "aside", "form", "noscript", "figure"]):
            tag.decompose()

        # Find the richest content container
        body = (
            soup.find("article")
            or soup.find("main")
            or soup.find(id=re.compile(r"content|article|post|body", re.I))
            or soup.find(class_=re.compile(r"content|article|post|entry|body", re.I))
            or soup.body
        )
        if body is None:
            return []

        HEADING_TAGS = {"h1", "h2", "h3", "h4"}
        sections: list[ParsedSection] = []
        current_heading = "Introduction"
        current_paragraphs: list[str] = []

        def flush(heading: str, paragraphs: list[str]) -> None:
            content = "\n\n".join(p for p in paragraphs if p.strip())
            if content.strip():
                sections.append(ParsedSection(
                    heading=heading,
                    type=self._infer_section_type(heading),
                    content=content,
                    page_start=0,
                    page_end=0,
                ))

        for element in body.descendants:
            if not isinstance(element, Tag):
                continue
            if element.name in HEADING_TAGS:
                heading_text = element.get_text(" ", strip=True)
                if heading_text:
                    flush(current_heading, current_paragraphs)
                    current_heading = heading_text
                    current_paragraphs = []
            elif element.name == "p":
                text = element.get_text(" ", strip=True)
                if text:
                    current_paragraphs.append(text)

        flush(current_heading, current_paragraphs)
        return sections

    def _extract_web_references(
        self, html: str, base_url: str
    ) -> list[ParsedReference]:
        """
        Extract pseudo-references from a web page:
        1. Outbound links to known paper repositories (arXiv, DOI, ACL, etc.)
        2. Numbered reference list items ([1] Author et al. ...)
        """
        from bs4 import BeautifulSoup
        from urllib.parse import urljoin, urlparse

        soup = BeautifulSoup(html, "lxml")
        refs: list[ParsedReference] = []
        seen_urls: set[str] = set()

        # --- 1. Harvest links to academic sources ---
        ACADEMIC_PATTERNS = re.compile(
            r"(arxiv\.org|doi\.org|aclanthology\.org|openreview\.net"
            r"|semanticscholar\.org|papers\.nips\.cc|proceedings\.mlr\.press"
            r"|aclweb\.org|dl\.acm\.org|ieeexplore\.ieee\.org)",
            re.I,
        )
        for a in soup.find_all("a", href=True):
            href = urljoin(base_url, a["href"])
            if href in seen_urls:
                continue
            if not ACADEMIC_PATTERNS.search(href):
                continue
            seen_urls.add(href)

            link_text = a.get_text(" ", strip=True)
            doi = self._doi_from_url(href)
            year = self._year_from_url(href)

            refs.append(ParsedReference(
                title=link_text or href,
                doi=doi,
                url=href,
                year=year,
                context=self._surrounding_text(a, chars=200),
            ))

        # --- 2. Numbered reference list items ---
        REF_ITEM = re.compile(r"^\s*\[?\d+\]?\s+.{20,}", re.M)
        # Look for <ol>/<ul> near a "References" heading
        ref_section = None
        for heading in soup.find_all(re.compile(r"^h[1-4]$")):
            if re.search(r"reference|bibliograph", heading.get_text(), re.I):
                ref_section = heading
                break

        if ref_section:
            container = ref_section.find_next_sibling(
                ["ol", "ul", "div", "section"]
            )
            if container:
                for li in container.find_all(["li", "p"]):
                    text = li.get_text(" ", strip=True)
                    if not text or len(text) < 20:
                        continue
                    doi = self._doi_from_text(text)
                    year = self._year_from_text(text)
                    refs.append(ParsedReference(
                        title=text[:200],
                        doi=doi,
                        year=year,
                        context=text[:300],
                    ))

        return refs[:50]  # cap to avoid noise from link-heavy pages

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _doi_from_url(url: str) -> Optional[str]:
        m = re.search(r"doi\.org/(.+)", url)
        return m.group(1) if m else None

    @staticmethod
    def _doi_from_text(text: str) -> Optional[str]:
        m = re.search(r"10\.\d{4,}/\S+", text)
        return m.group(0).rstrip(".,)") if m else None

    @staticmethod
    def _year_from_url(url: str) -> Optional[int]:
        # arXiv IDs like 2310.12345
        m = re.search(r"/(2[01]\d{2})\.", url)
        if m:
            return int(m.group(1))
        return None

    @staticmethod
    def _year_from_text(text: str) -> Optional[int]:
        m = re.search(r"\b(19|20)\d{2}\b", text)
        return int(m.group(0)) if m else None

    @staticmethod
    def _surrounding_text(tag, chars: int = 200) -> str:
        """Return up to `chars` characters of text around a tag."""
        parent = tag.parent
        if parent is None:
            return ""
        return parent.get_text(" ", strip=True)[:chars]

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
