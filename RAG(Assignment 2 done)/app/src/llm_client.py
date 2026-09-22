import logging
import base64
from typing import AsyncGenerator, Optional

from openai import AzureOpenAI, AsyncAzureOpenAI
from app.src.config import settings

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self, temperature: float = 0.2, timeout: int = 30) -> None:
        self.temperature = temperature
        self.timeout = timeout
        self.deployment_name = settings.azure_llm_deployment

       
        self.client = AzureOpenAI(
            api_key=settings.azure_openai_api_key,
            azure_endpoint=settings.azure_openai_endpoint,
            api_version=settings.azure_openai_api_version,
        )

        self.async_client = AsyncAzureOpenAI(
            api_key=settings.azure_openai_api_key,
            azure_endpoint=settings.azure_openai_endpoint,
            api_version=settings.azure_openai_api_version,
        )

    async def describe_image_for_search(self, question: str, image_bytes: bytes) -> str:
        """Analyze image to create a text query for searching the FAISS index."""
        b64_image = base64.b64encode(image_bytes).decode("utf-8")

        prompt = (
            f"User Question: {question}\n"
            "Analyze this image. What specific technical terms, part numbers, or visual "
            "details should I search for in the documentation to answer this? "
            "Output ONLY the search keywords."
        )

        response = await self.async_client.chat.completions.create(
            model=self.deployment_name,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{b64_image}"
                            },
                        },
                    ],
                }
            ],
            max_tokens=100,
        )
        return response.choices[0].message.content

    async def generate_stream(
        self,
        prompt: str,
        image_bytes: Optional[bytes] = None,
    ) -> AsyncGenerator[str, None]:
        """Supports both text-only and multimodal streaming."""
        content = [{"type": "text", "text": prompt}]

        if image_bytes:
            b64_image = base64.b64encode(image_bytes).decode("utf-8")
            content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{b64_image}"
                    },
                }
            )

        try:
            stream = await self.async_client.chat.completions.create(
                model=self.deployment_name,
                messages=[{"role": "user", "content": content}],
                temperature=self.temperature,
                stream=True,
                timeout=self.timeout,
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as exc:
            logger.exception("LLM stream failed")
            raise RuntimeError("LLM call failed") from exc

    async def get_intent(self, text: str) -> str:
        """Uses the LLM to categorize the user's intent (Fast Async Call)."""
        prompt = (
            "You are an intent classifier. Categorize the user input into ONE word:\n"
            "1. GREETING: If the user says hi, hello, or asks 'how are you'.\n"
            "2. DOCUMENT_QUERY: If the user asks about technical data, manuals, or specific info.\n"
            "3. OTHER: For everything else (thanks, goodbye).\n\n"
            f"Input: {text}\nCategory:"
        )

        try:
           
            response = await self.async_client.chat.completions.create(
                model=self.deployment_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0, 
                max_tokens=10
            )
            return response.choices[0].message.content.strip().upper()
        except Exception:
            return "DOCUMENT_QUERY" # Fallback

    def generate(self, prompt: str) -> str:
        """Synchronous generation (used for voice)."""
        response = self.client.chat.completions.create(
            model=self.deployment_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
        )
        return response.choices[0].message.content