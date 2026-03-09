
import logging
import azure.functions as func
import base64
import requests
import io
import pdfplumber
import docx
from PIL import Image
import easyocr

reader = easyocr.Reader(['en'])

def extract_from_pdf(file_bytes):
    text = ""
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

def extract_from_docx(file_bytes):
    doc = docx.Document(io.BytesIO(file_bytes))
    return "\n".join([p.text for p in doc.paragraphs])

def extract_from_image(file_bytes):
    image = Image.open(io.BytesIO(file_bytes))
    results = reader.readtext(image)
    return " ".join([r[1] for r in results])

def structure_text(text):
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    structured = {
        "raw_text": text,
        "lines": lines,
        "possible_email": None,
        "possible_phone": None
    }

    for line in lines:
        if "@" in line and "." in line and structured["possible_email"] is None:
            structured["possible_email"] = line
        if any(char.isdigit() for char in line) and structured["possible_phone"] is None and len(line) >= 10:
            structured["possible_phone"] = line

    return structured

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Resume extraction function triggered.")

    try:
        body = req.get_json()
    except:
        return func.HttpResponse("Invalid JSON body", status_code=400)

    file_url = body.get("fileUrl")
    file_base64 = body.get("fileContent")

    if file_url:
        response = requests.get(file_url)
        file_bytes = response.content
        file_name = file_url.split("/")[-1].lower()
    elif file_base64:
        file_bytes = base64.b64decode(file_base64)
        file_name = "uploaded_file"
    else:
        return func.HttpResponse("Provide fileUrl or fileContent", status_code=400)

    text = ""

    if file_name.endswith(".pdf"):
        text = extract_from_pdf(file_bytes)
    elif file_name.endswith(".docx"):
        text = extract_from_docx(file_bytes)
    else:
        text = extract_from_image(file_bytes)

    structured = structure_text(text)

    return func.HttpResponse(
        json.dumps(structured),
        mimetype="application/json",
        status_code=200
    )
