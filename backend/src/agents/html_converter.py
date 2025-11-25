import re
import logging
import html
from openai import AsyncOpenAI  # Changed import
from ..config import settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class HtmlResumeConverter:
    """
    HtmlResumeConverter: LLM merges HTML template + raw text.
    HTML is more forgiving than Typst, so we rely more on the LLM's ability 
    to generate valid code, while performing basic cleanup on the result.
    """

    def __init__(self):
        logger.info("Initializing HtmlResumeConverter with OpenAI Direct API...")
        
        # Initialize the Async Client
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY
        )
        
        # Define the model (You can change this to "gpt-4-turbo" or "gpt-3.5-turbo" if needed)
        self.model_name = "gpt-4.1"

        # Store System prompt as a class attribute to be used in the API call
        self.system_prompt = """
You are an expert HTML & CSS Resume Generator.
INPUT: 1) An HTML/CSS template (Raw code), 2) Unstructured Resume Text.
TASK:
1. Analyse the unstructured text.
2. Populate the HTML template with the data.
3. Ensure the CSS is "Internal" (placed inside <style> tags in the <head>) so the output is a single self-contained file.
4. TEXT SAFETY: strictly escape HTML special characters within the content (e.g., "C&C++" becomes "C&amp;C++").
5. Do NOT output Markdown (no ```html fences). Output PURE CODE only.
"""

    async def strip_fenced_code(self, text: str) -> str:
        """Removes markdown code fences if the LLM includes them."""
        # Remove starting ```html or ```
        text = re.sub(r"^```[a-zA-Z0-9_+-]*\s*\n", "", text.strip())
        # Remove ending ```
        text = re.sub(r"\n```$", "", text.strip())
        return text

    # ---------------------------
    # Sanitizer utilities
    # ---------------------------
    def _convert_markdown_to_html_tags(self, text: str) -> str:
        """
        Sometimes LLMs slip Markdown into HTML (e.g. <li>**Role**</li>).
        This converts basic bold/italic markdown to HTML tags.
        """
        # Convert **text** to <strong>text</strong>
        text = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", text)
        # Convert *text* to <em>text</em>
        text = re.sub(r"\*(.*?)\*", r"<em>\1</em>", text)
        return text

    def _ensure_valid_structure(self, html_content: str) -> str:
        """
        Basic check to ensure the LLM didn't truncate the file.
        """
        if "</html>" not in html_content:
            logger.warning("HTML output appears truncated (missing </html>).")
        return html_content

    def sanitize_html_merged(self, merged: str) -> str:
        """
        Pipeline to clean up the LLM output.
        """
        logger.info("Sanitizer: starting HTML pipeline...")

        # 1. Remove Markdown Fences (Double check)
        cleaned = merged.replace("```html", "").replace("```", "")

        # 2. Convert accidental Markdown bold/italics to HTML
        cleaned = self._convert_markdown_to_html_tags(cleaned)

        # 3. Ensure newlines are standardized
        cleaned = cleaned.replace("\r\n", "\n")

        # 4. Structure check
        cleaned = self._ensure_valid_structure(cleaned)

        logger.info("Sanitizer: completed")
        return cleaned

    # --------------------------
    # Main entry: merge -> sanitize
    # --------------------------
    async def convert_to_html(self, html_template: str, json_data: str) -> dict:
        """
        1. Ask LLM to merge raw_text into html_template.
        2. Sanitize the result.
        3. Return valid HTML string.
        """
        raw_text = json_data
        logger.info("Starting convert_to_html: merging with LLM.")

        try:
            user_msg = f"""
Here is the HTML/CSS Template:

{html_template}
Here is the raw extracted resume text:
-----
{raw_text}
-----

TASK: Fill the template with the raw text. Keep the exact layout and CSS of the template.
IMPORTANT: Return ONLY the raw HTML code. No explanations.
"""
            logger.debug("Sending merge request to OpenAI...")
            
            # Construct the messages payload
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_msg}
            ]

            # Call OpenAI Chat Completion
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0,  # Low temperature for more deterministic code generation
            )
            
            # Extract content
            llm_output = response.choices[0].message.content
            
            # Initial cleanup
            merged = await self.strip_fenced_code(llm_output)
            
            # Run sanitizer
            logger.info("Merge completed. Running sanitizer...")
            final_html = self.sanitize_html_merged(merged)
            
            logger.info("Sanitization finished. Returning final HTML.")
            return {"success": True, "html": final_html}

        except Exception as e:
            logger.exception("HTML Conversion failed")
            return {"success": False, "error": str(e)}