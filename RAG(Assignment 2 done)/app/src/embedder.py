from typing import List
import logging
from openai import AzureOpenAI

from app.src.config import settings

logger = logging.getLogger(__name__)


class Embedder:
    """
    Azure OpenAI embedding client.
    """

    def __init__(self) -> None:
        self.client = AzureOpenAI(
            api_key=settings.azure_openai_api_key,
            azure_endpoint=settings.azure_openai_endpoint,
            api_version=settings.azure_openai_api_version,
        )

       
        self.deployment_name = settings.azure_embedding_deployment

        logger.info(
            "Initialized Azure Embedder with deployment=%s",
            self.deployment_name
        )

    def embed(self, texts: List[str]) -> List[List[float]]:
        try:
            response = self.client.embeddings.create(
                model=self.deployment_name,
                input=texts
            )

            return [item.embedding for item in response.data]

        except Exception as exc:
            logger.exception("Embedding generation failed")
            raise RuntimeError("Embedding failed") from exc
