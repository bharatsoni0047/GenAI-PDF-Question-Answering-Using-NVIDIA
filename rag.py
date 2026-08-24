"""Retrieval and answer generation, kept out of the UI so both Streamlit and the eval
script use the exact same code path.
"""
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_nvidia_ai_endpoints import ChatNVIDIA

import config
from ingest import get_embeddings

PROMPT = ChatPromptTemplate.from_template(
    """Answer the question using ONLY the context below.
Each excerpt is labelled with the file and page it came from.
Cite the file and page for every fact you use, like [acsbr-016.pdf p.4].
If the context does not contain the answer, say so plainly - do not guess.

<context>
{context}
</context>

Question: {question}"""
)

_store = None


def get_store():
  """The persisted Chroma collection, opened once."""
  global _store
  if _store is None:
    _store = Chroma(persist_directory=config.CHROMA_DIR, embedding_function=get_embeddings())
  return _store


def retrieve(question, k=config.TOP_K):
  """The k most relevant chunks. Returns the documents themselves, so the caller keeps
  the metadata - the old code returned bare text and the source was lost."""
  return get_store().similarity_search(question, k=k)


def format_context(docs):
  """Label every excerpt with its file and page, so the model can cite it."""
  return "\n\n".join(
      f"[{d.metadata.get('source_file', '?')} p.{d.metadata.get('page_number', '?')}]\n"
      f"{d.page_content}" for d in docs)


def answer(question, k=config.TOP_K):
  """Retrieve ONCE, then generate. Returns (answer_text, source_documents).

  The previous version invoked the retriever inside the chain and then a second time to
  populate the 'similarity search' expander - so every question paid for retrieval twice
  and the two results could even differ. Retrieving once and passing the documents along
  fixes both."""
  config.require_key()
  docs = retrieve(question, k)
  if not docs:
    return ("Nothing is indexed yet - run `python ingest.py` first.", [])
  llm = ChatNVIDIA(model=config.LLM_MODEL, api_key=config.NVIDIA_API_KEY)
  reply = (PROMPT | llm).invoke({"context": format_context(docs), "question": question})
  return reply.content, docs
