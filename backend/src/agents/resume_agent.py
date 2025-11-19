from agent_framework.azure import AzureOpenAIChatClient
from ..config import settings

class TestAgent:
    def __init__(self):
        self.client = AzureOpenAIChatClient(
            endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            deployment_name=settings.AZURE_OPENAI_DEPLOYMENT_NAME
        )

        self.agent = self.client.create_agent(
            name="Resume GPT",
            system_prompt="You are a helpful test agent.")

    async def test_connection(self):
        try:
            response = await self.agent.run("Say Connection Successful if you can hear me.")
            return {"success": True, "response": response.text}
        except Exception as e:
            return {"success": False, "error": str(e)}
            