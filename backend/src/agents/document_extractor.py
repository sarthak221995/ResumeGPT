import time
import logging
from openai import AsyncOpenAI
from ..config import settings  # your config file

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class DocumentExtractor:
    """
    Ultra-fast document extractor using OpenAI Responses API.
    Supports: PDF, DOCX, PPTX, XLSX, TXT, Images.
    """

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o"  # must be gpt-4o or gpt-4.1 for direct file ingestion

    # ------------------------------------------------------------------
    # MAIN: Extract from in-memory file bytes
    # ------------------------------------------------------------------
    async def extract_from_bytes(self, file_bytes: bytes, filename: str):
        start_total = time.time()

        try:
            # ----------------------------------------------------------
            # STEP 1 — Upload file to OpenAI (in memory)
            # ----------------------------------------------------------
            upload = await self.client.files.create(
                file=(filename, file_bytes),
                purpose="assistants"
            )
            file_id = upload.id
            logger.info(f"📤 Uploaded file {filename} (file_id={file_id})")

            # ----------------------------------------------------------
            # STEP 2 — Call Responses API (supports file ingestion)
            # ----------------------------------------------------------
            logger.info("🤖 Calling gpt-4o for document extraction...")

            response = await self.client.responses.create(
                model=self.model,
                input=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_file", "file_id": file_id},  # Changed from "file" to "input_file"
                            {
                                "type": "input_text",  # Changed from "text" to "input_text"
                                "text": (
                                    "Extract all textual content from this document. "
                                    "Preserve reading order. Output clean plain text only. "
                                    "No JSON, no markdown, no commentary."
                                ),
                            },
                        ],
                    }
                ],
                max_output_tokens=8000
            )

            extracted_text = response.output_text

            total_time = time.time() - start_total
            logger.info(f"🚀 Extraction finished in {total_time:.2f}s")
            logger.info(f"Extracted Text Sample : {extracted_text[:500]}")

            return {
                "success": True,
                "extracted_data": extracted_text,
                "method": "responses_api_direct_file",
                "execution_time": total_time,
            }

        except Exception as e:
            logger.exception("❌ Extraction failed")
            return {"success": False, "error": str(e)}