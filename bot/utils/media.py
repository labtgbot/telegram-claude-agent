import asyncio
import tempfile
import os
from typing import Optional

async def transcribe_voice(audio_data: bytes) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _transcribe_sync, audio_data)

def _transcribe_sync(audio_data: bytes) -> str:
    try:
        import whisper
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
            f.write(audio_data)
            temp_path = f.name
        # Load model (cache on first use)
        if not hasattr(_transcribe_sync, "model"):
            _transcribe_sync.model = whisper.load_model("base")
        model = _transcribe_sync.model
        result = model.transcribe(temp_path)
        os.remove(temp_path)
        return result["text"]
    except Exception:
        return ""

async def extract_document_text(mime_type: str, data: bytes) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _extract_sync, mime_type, data)

def _extract_sync(mime_type: str, data: bytes) -> str:
    try:
        if mime_type == "application/pdf":
            from PyPDF2 import PdfReader
            import io
            reader = PdfReader(io.BytesIO(data))
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text.strip()
        elif mime_type == "text/plain":
            return data.decode('utf-8', errors='ignore')
        elif mime_type in [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
        ]:
            import docx
            import io
            doc = docx.Document(io.BytesIO(data))
            text = "\n".join([para.text for para in doc.paragraphs])
            return text.strip()
        else:
            return ""
    except Exception:
        return ""