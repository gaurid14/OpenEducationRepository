from PyPDF2 import PdfReader

def read_pdf(file_path):
    """Return page count and combined text from PDF."""
    reader = PdfReader(file_path)
    text = "\n".join([page.extract_text() or "" for page in reader.pages])
    return len(reader.pages), text
