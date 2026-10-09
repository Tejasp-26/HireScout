import io
import re

from pypdf import PdfReader


class EmptyPdfError(ValueError):
    """The PDF has no extractable text layer (usually a scanned image)."""


def repair_letter_spacing(text: str) -> str:
    """Rejoin text that was extracted as "J A N E  D O E".

    Some design-tool exports (Canva and friends) come out of PDF extraction
    with a space between every character and a wider gap at real word
    boundaries. If most tokens are single characters, treat runs of 2+
    spaces as word breaks and squash the single spaces inside each word.
    """
    tokens = text.split()
    if not tokens:
        return text

    single_char_ratio = sum(1 for t in tokens if len(t) == 1) / len(tokens)
    if single_char_ratio <= 0.5:
        return text

    repaired = []
    for line in text.split("\n"):
        words = re.split(r" {2,}", line)
        repaired.append(" ".join(word.replace(" ", "") for word in words))
    return "\n".join(repaired)


def extract_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages = [page.extract_text() or "" for page in reader.pages]
    text = repair_letter_spacing("\n".join(pages))

    # Normalise whitespace without destroying line structure.
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    if len(text) < 30:
        raise EmptyPdfError("No extractable text found (is this a scanned PDF?)")
    return text
