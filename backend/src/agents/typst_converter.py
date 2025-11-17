from agent_framework.azure import AzureOpenAIChatClient
from ..config import settings
import json
import re

class TypstConverter:
    def __init__(self):
        self.client = AzureOpenAIChatClient(
            endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            deployment_name=settings.AZURE_OPENAI_DEPLOYMENT_NAME
        )

        self.agent = self.client.create_agent(
            name="Typst Resume Generator",
            system_prompt="""
You are an expert Typst resume generator.

TASK:
You will receive:
1. A Typst TEMPLATE (.typ code)
2. A JSON resume object

Your job:
- Merge JSON content into the Typst template.
- Fill ONLY the sections that already exist in the template.
- If JSON contains extra fields not in the template → skip them.
- If template contains sections missing in JSON → delete/skip safely.
- Do NOT hallucinate any content.
- Preserve the Typst formatting exactly as provided.

STRICT OUTPUT RULE:
Return ONLY valid Typst code from the first line to the last line of the template.
No markdown, no comments, no explanations.

MERGING RULES:
- Replace placeholders like {{field}} with JSON values.
- If the template uses loops (#for item in list:) then insert repeated Typst blocks accordingly.
- Convert bullet lists to the same bullet style used in template.
- Escape Typst-sensitive characters: #, [, ], {, }, $, %, &.

Your output must be:
✔ A SINGLE, fully formatted .typ file
✔ 100% valid Typst syntax
✔ Never wrapped inside code fences
✔ No commentary; only raw Typst output
"""
        )

    async def strip_fenced_code(self, text):
        # Strip ```typst or ``` or similar
        text = re.sub(r"^```[a-zA-Z0-9_+-]*\s*\n", "", text)
        text = re.sub(r"\n```$", "", text)
        return text

    async def convert_to_typst(self, typst_template: str, json_data: dict) -> dict:
        """
        typst_template: raw .typ template string
        json_data: resume JSON object
        """
        try:
            message = f"""
Here is the Typst template:

===== TEMPLATE START =====
{typst_template}
===== TEMPLATE END =====

Here is the JSON resume data:
{json.dumps(json_data, indent=2)}

IMPORTANT:
Output MUST contain ONLY valid Typst code.
Do NOT wrap in ```typst or any code blocks.
Do NOT add explanations.

Generate the final Typst resume:

"""
            response = await self.agent.run(message)
            return {"success": True, "typst": await self.strip_fenced_code(response.text)}

        except Exception as e:
            return {"success": False, "error": str(e)}
