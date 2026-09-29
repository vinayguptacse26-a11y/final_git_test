import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from retriever import load_hybrid_retriever

# Load environment variables (e.g., GROQ_API_KEY)
load_dotenv()

class CSVHybridRAG:
    """
    A unified interface for querying the CSV Hybrid RAG system.
    Designed to be easily imported and used within external tools like Power BI.
    """
    def __init__(self, index_dir: str = "indexes/", groq_model: str = "openai/gpt-oss-120b"):
        """
        Initializes the RAG system by loading the hybrid retriever and setting up the Groq LLM.
        """
        # Ensure Groq API key is present
        if "GROQ_API_KEY" not in os.environ:
            raise ValueError("GROQ_API_KEY environment variable not found. Please set it.")
            
        print("Initializing Hybrid Retriever...")
        self.retriever = load_hybrid_retriever(index_dir=index_dir)
        
        print(f"Initializing Groq LLM ({groq_model})...")
        self.llm = ChatGroq(model=groq_model, temperature=0.2)
        
        # Define the system prompt
        template = """You are a helpful data assistant. Use the following retrieved context from a CSV database to answer the user's question.
If you cannot answer the question based on the context, say that you don't know. Do not make up information.

Context:
{context}

Question: {question}

Answer:"""
        self.prompt = ChatPromptTemplate.from_template(template)
        
        # Build the LangChain Expression Language (LCEL) chain
        self.chain = (
            {"context": self.retriever | self._format_docs, "question": RunnablePassthrough()}
            | self.prompt
            | self.llm
            | StrOutputParser()
        )
        
    def _format_docs(self, docs):
        """Helper to format retrieved Langchain Documents into a single string."""
        formatted = []
        for d in docs:
            # You can also include row index or metadata here if useful
            formatted.append(f"---\n{d.page_content}")
        return "\n".join(formatted)

    def query(self, user_question: str) -> str:
        """
        Executes a query against the RAG system (blocks until full answer is ready).
        """
        try:
            return self.chain.invoke(user_question)
        except Exception as e:
            return f"An error occurred during query execution: {str(e)}"

    def stream_query(self, user_question: str):
        """
        Executes a query and yields the response chunk by chunk for instant streaming.
        """
        try:
            for chunk in self.chain.stream(user_question):
                yield chunk
        except Exception as e:
            yield f"An error occurred: {str(e)}"
            
    def get_raw_context(self, user_question: str) -> list:
        """
        Returns the raw retrieved documents without LLM generation. 
        Useful for Power BI if you just want to filter/display the most relevant CSV rows.
        """
        return self.retriever.invoke(user_question)

if __name__ == "__main__":
    # Example usage:
    # rag = CSVHybridRAG("indexes/")
    # answer = rag.query("What products are out of stock?")
    # print(answer)
    pass
