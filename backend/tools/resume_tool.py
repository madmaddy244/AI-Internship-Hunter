from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader

MAX_RESUME_BYTES = 10 * 1024 * 1024


class ResumeParseError(ValueError):
    pass


def extract_pdf_text(file_bytes: bytes) -> str:
    if not file_bytes:
        raise ResumeParseError("The uploaded resume is empty.")
    if len(file_bytes) > MAX_RESUME_BYTES:
        raise ResumeParseError("The PDF must be 10 MB or smaller.")
    if not file_bytes.lstrip().startswith(b"%PDF-"):
        raise ResumeParseError("Upload a valid PDF resume.")
    try:
        reader = PdfReader(BytesIO(file_bytes), strict=False)
        if reader.is_encrypted:
            raise ResumeParseError("Password-protected PDFs are not supported.")
        text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    except ResumeParseError:
        raise
    except Exception as error:
        raise ResumeParseError("This PDF could not be read. Try exporting it again.") from error
    if not text:
        raise ResumeParseError(
            "No selectable text was found in this PDF. Upload a text-based PDF rather than a scanned image."
        )
    return text[:60_000]
