"""Streamlit UI. Run: streamlit run app.py   (after: python ingest.py)"""
import streamlit as st

import config
from rag import answer

st.set_page_config(page_title="PDF Q&A - NVIDIA NIM", layout="centered")
st.title("PDF Question Answering")
st.caption(f"Embeddings: {config.EMBED_MODEL}  |  LLM: {config.LLM_MODEL}")

if not config.NVIDIA_API_KEY:
  st.error("NVIDIA_API_KEY is not set. Copy .env.example to .env and add your key.")
  st.stop()

question = st.text_input("Ask a question about the indexed PDFs")

if question:
  with st.spinner("Searching the documents..."):
    text, docs = answer(question)
  st.write(text)
  with st.expander(f"Sources ({len(docs)} excerpts)"):
    # the SAME documents the answer was written from - not a second, separate search
    for doc in docs:
      st.markdown(f"**{doc.metadata.get('source_file', '?')}** "
                  f"- page {doc.metadata.get('page_number', '?')}")
      st.write(doc.page_content)
      st.divider()
