from agent_framework.azure import AzureOpenAIChatClient
from ..config import settings
import re
import logging

logger = logging.getLogger(__name__)

class TypstModifier:
    def __init__(self):
        # Initialize the same Azure OpenAI Client
        self.client = AzureOpenAIChatClient(
            endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            deployment_name=settings.AZURE_OPENAI_DEPLOYMENT_NAME
        )

        self.agent = self.client.create_agent(
            name="Typst Resume Modifier",
            system_prompt="""
You are an expert Typst code modifier.
Your task is to take existing Typst code and modify it according to a user's natural language prompt.

RULES:
1. Preserve the original structure and overall document setup (imports, set commands) unless explicitly told to change them.
2. Only make the *exact* changes requested by the user prompt.
3. If the user asks for a simple content change (e.g., "change the email"), find the old value and replace it with the new value.
4. If the user asks for a style change (e.g., "make the name bold"), find the relevant code block and apply the necessary Typst commands (e.g., use #set text() or apply a formatting function).
5. Do NOT add any extra commentary, markdown formatting, or explanations.

STRICT OUTPUT RULE:
Return ONLY the full, modified Typst code.
"""
        )

    async def strip_fenced_code(self, text):
        # Strip ```typst or ``` or similar
        text = re.sub(r"^```[a-zA-Z0-9_+-]*\s*\n", "", text)
        text = re.sub(r"\n```$", "", text)
        return text

    async def modify_typst(self, typst_code: str, prompt: str) -> dict:
        """
        typst_code: the existing .typ file content
        prompt: the user's modification request
        """
        logger.info(f"🔄 Modifying Typst code with prompt: {prompt}")
        try:
            message = f"""
Here is the current Typst code:

===== CODE START =====
{typst_code}
===== CODE END =====

Here is the user's modification request:
{prompt}

IMPORTANT:
Output MUST contain ONLY the full, modified Typst code.
Do NOT wrap in code blocks. Do NOT add explanations.

Generate the final modified Typst resume:
"""
            response = await self.agent.run(message)
            
            modified_typst = await self.strip_fenced_code(response.text)
            
            logger.info("✅ Modification complete.")
            return {"success": True, "modified_typst": modified_typst}

        except Exception as e:
            logger.error(f"❌ Modification failed: {str(e)}")
            return {"success": False, "error": f"Modification failed: {str(e)}"}