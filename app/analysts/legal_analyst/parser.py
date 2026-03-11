from pathlib import Path
from typing import Optional
import pdfplumber
import docx


class DocumentParser:
    """
    Responsible for extracting raw text from legal documents.
    Supports PDF, DOCX and TXT formats.
    """

    SUPPORTED_FORMATS = {".pdf", ".docx", ".txt"}

    def parse(self, file_path: str) -> str:

        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if path.suffix.lower() not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported file type: {path.suffix}")

        if path.suffix == ".pdf":
            return self._parse_pdf(path)

        if path.suffix == ".docx":
            return self._parse_docx(path)

        if path.suffix == ".txt":
            return self._parse_txt(path)

        raise ValueError("Invalid document format")

    def _parse_pdf(self, path: Path) -> str:

        text = []

        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                page_text: Optional[str] = page.extract_text()

                if page_text:
                    text.append(page_text)

        return "\n".join(text)

    def _parse_docx(self, path: Path) -> str:

        doc = docx.Document(path)

        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

        return "\n".join(paragraphs)

    def _parse_txt(self, path: Path) -> str:

        with open(path, "r", encoding="utf-8") as f:
            return f.read()