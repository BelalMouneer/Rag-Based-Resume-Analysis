from llama_index.llms.groq import Groq # type: ignore
from llama_index.core import PromptTemplate # type: ignore
from langchain_community.embeddings.huggingface import HuggingFaceEmbeddings
from llama_index.core import Settings # type: ignore
from llama_index.embeddings.langchain import LangchainEmbedding # type: ignore
from llama_index.core.node_parser import SentenceSplitter # type: ignore
import os
from dotenv import load_dotenv
load_dotenv()

def get_llm_settings(contect_window: int, max_new_token: int):
    system_prompt = """
    You are a Q&A assistant. Your goal is to answer questions based on the text \
    given. You'll also provide the previous chat history if there is any so \
    answer to the last question asked.
    """

    query_wrapper_prompt = PromptTemplate("<|USER|>{query_str}<|ASSISTANT|>")

    llm = Groq(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        api_key=os.getenv("GROQ_API_KEY"),
        context_window=contect_window,
        max_tokens=max_new_token,
        temperature=0.0,
        system_prompt=system_prompt,
        query_wrapper_prompt=query_wrapper_prompt
    )

    embed_model = LangchainEmbedding(
        HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2"))

    Settings.llm = llm
    Settings.embed_model = embed_model
    Settings.node_parser = SentenceSplitter(chunk_size=1024)
    settings = Settings

    return settings