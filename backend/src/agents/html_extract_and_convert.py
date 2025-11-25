import logging
import time
from pathlib import Path

from fastapi import UploadFile
from openai import AsyncOpenAI

from ..config import settings

logger = logging.getLogger(__name__)

class UnifiedResumeProcessor:
    """
    MERGED EXTRACTOR & CONVERTER (File Upload Version)
    ----------------------------
    Uses OpenAI's direct file processing (Responses API pattern) to read documents
    and generate HTML in a SINGLE API call.
    Replaces Vision/Image logic with File ID logic.
    """
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o-mini" 

    async def process(self, file: UploadFile, template_id: str, templates_dir: Path) -> dict:
        try:
            logger.info(f"🚀 Starting Unified Process (File Upload) for {file.filename}")

            # --- STEP 1: UPLOAD FILE TO OPENAI ---
            # We upload the raw file bytes directly, exactly like DocumentExtractor
            file_content = await file.read()
            
            upload = await self.client.files.create(
                file=(file.filename, file_content),
                purpose="assistants"
            )
            file_id = upload.id
            logger.info(f"📤 Uploaded file to OpenAI (file_id={file_id})")

            # --- STEP 2: LOAD TEMPLATE ---
            # Locate Template
            template_path = templates_dir / f"{template_id}.html"
            if not template_path.exists():
                template_path = templates_dir / template_id
                if not template_path.exists():
                     template_path = templates_dir / "classic.html"
            
            if not template_path.exists():
                return {"success": False, "error": f"Template {template_id} not found"}

            with open(template_path, "r", encoding="utf-8") as f:
                html_template_str = f.read()

            # --- STEP 3: CALL RESPONSES API ---
            # We merge the extraction and HTML filling into one prompt
            
            system_instruction = """
            You are an Expert Resume Engineer.
            
            TASK:
            1. Read the attached resume file.
            2. Extract all relevant data (Experience, Education, Skills, Contact).
            3. Populate the HTML Template provided below with this data.
            
            CRITICAL RULES:
            - **Preserve Layout:** Do NOT change the CSS or structure of the HTML.
            - **Smart Fill:** Replace placeholder text with real extracted data.
            - **Output:** Return ONLY the raw valid HTML code. No markdown fences.
            """

            # Construct the user text prompt containing the template
            user_text_prompt = (
                f"{system_instruction}\n\n"
                "Here is the target HTML Template:\n"
                "```html\n" + 
                html_template_str + 
                "\n```\n\n"
                "INSTRUCTIONS: Fill this template using the data from the attached file. Return only the final HTML."
            )

            # Use the responses.create pattern from your DocumentExtractor
            response = await self.client.responses.create(
                model=self.model,
                input=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_file", "file_id": file_id},
                            {"type": "input_text", "text": user_text_prompt}
                        ],
                    }
                ],
                max_output_tokens=8000
            )

            # --- STEP 4: CLEANUP ---
            generated_html = response.output_text
            
            # Simple cleanup in case the AI added markdown fences
            generated_html = generated_html.replace("```html", "").replace("```", "").strip()

            return {"success": True, "html_code": generated_html}

        except Exception as e:
            logger.error(f"Unified Process Failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

# Singleton instance
unified_processor = UnifiedResumeProcessor()