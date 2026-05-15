import asyncio
import os
import tempfile

import structlog

logger = structlog.get_logger()


async def transcribe_voice(audio_data: bytes) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _transcribe_sync, audio_data)


def _transcribe_sync(audio_data: bytes) -> str:
    temp_path = None
    try:
        import whisper

        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
            f.write(audio_data)
            temp_path = f.name

        if not hasattr(_transcribe_sync, "model"):
            _transcribe_sync.model = whisper.load_model("base")
        model = _transcribe_sync.model
        result = model.transcribe(temp_path)
        return result["text"]
    except Exception as exc:
        logger.warning("transcribe_failed", error=str(exc))
        return ""
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


async def extract_document_text(mime_type: str, data: bytes) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _extract_sync, mime_type, data)


def _extract_sync(mime_type: str, data: bytes) -> str:
    if not data:
        return ""
    normalized = (mime_type or "").strip().lower()
    try:
        if normalized == "application/pdf":
            import io
            from PyPDF2 import PdfReader

            reader = PdfReader(io.BytesIO(data))
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text.strip()
        if normalized == "text/plain":
            return data.decode("utf-8", errors="ignore").strip()
        if normalized in (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
        ):
            import io
            import docx

            doc = docx.Document(io.BytesIO(data))
            text = "\n".join(para.text for para in doc.paragraphs)
            return text.strip()
        logger.info("extract_document_unknown_mime", mime_type=mime_type)
        return ""
    except Exception as exc:
        logger.warning(
            "extract_document_failed", mime_type=mime_type, error=str(exc)
        )
        return ""
