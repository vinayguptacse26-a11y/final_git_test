from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Azure OpenAI
    azure_openai_api_key: str
    azure_openai_endpoint: str
    azure_openai_api_version: str
    azure_llm_deployment: str

   
    azure_embedding_deployment: str
    

    speech_key: str
    speech_region: str
    speech_endpoint: str


    model_config = SettingsConfigDict(
        env_file=".env", 
        extra="ignore" 
    )

settings = Settings()