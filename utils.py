from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from pinecone_text.sparse import SpladeEncoder 
import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

def get_dense_embedder():
	embedder = OpenAIEmbeddings(
		model=st.secrets["OPENAI_EMBEDDING_MODEL"] or os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
		api_key=st.secrets["OPENAI_API_KEY"] or os.getenv("OPENAI_API_KEY")
	)
	return embedder

def get_sparse_embedder():
	embedder = SpladeEncoder()
	return embedder

def embed_dense_documents(texts):
    if not texts:
        return []
    embedder = get_dense_embedder()
    return embedder.embed_documents(texts)

def embed_sparse_documents(texts):
    if not texts:
        return []
    embedder = get_sparse_embedder()
    return embedder.encode_documents(texts)

def get_llm(streaming: bool = False):
	llm = ChatOpenAI(model=st.secrets["OPENAI_LLM_MODEL"] or os.getenv("OPENAI_LLM_MODEL", "gpt-4o-mini"), 
                    api_key=st.secrets["OPENAI_API_KEY"] or os.getenv("OPENAI_API_KEY"),
                    temperature=st.secrets["OPENAI_TEMPERATURE"] or os.getenv("OPENAI_TEMPERATURE", 0.7),
                    streaming=streaming)
	return llm