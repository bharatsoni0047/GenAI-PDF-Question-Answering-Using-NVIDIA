"""Build the vector index from every page of every PDF. Run once: python ingest.py

The previous version did this inside a Streamlit button handler and passed docs[:30] to
the splitter. PyPDFDirectoryLoader returns ONE document per page, so on this corpus of
63 pages that indexed the first 30 and silently discarded the rest - acsbr-017.pdf and
p70-178.pdf were never indexed at all, and any question about household income or
occupations could not be answered no matter how good the retriever was.
"""
import os

from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_chroma import Chroma
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

import config


def get_embeddings():
  """The NVIDIA embedding model - one instance, reused."""
  config.require_key()
  return NVIDIAEmbeddings(model=config.EMBED_MODEL, api_key=config.NVIDIA_API_KEY)


def load_pages():
  """Every page of every PDF, each tagged with its file name and page number so an
  answer can cite where it came from."""
  pages = PyPDFDirectoryLoader(config.PDF_DIR).load()
  for page in pages:
    page.metadata["source_file"] = os.path.basename(page.metadata.get("source", "unknown"))
    # pypdf counts from 0; humans count from 1
    page.metadata["page_number"] = page.metadata.get("page", 0) + 1
  return pages


def ingest():
  """Chunk every page, embed it and persist. Returns (pages, chunks, files)."""
  pages = load_pages()
  chunks = RecursiveCharacterTextSplitter(
      chunk_size=config.CHUNK_SIZE, chunk_overlap=config.CHUNK_OVERLAP).split_documents(pages)
  store = Chroma(persist_directory=config.CHROMA_DIR, embedding_function=get_embeddings())
  # reset first, so re-running does not stack a second copy of every chunk
  store.reset_collection()
  store.add_documents(chunks)
  return len(pages), len(chunks), sorted({p.metadata["source_file"] for p in pages})


if __name__ == "__main__":
  page_count, chunk_count, files = ingest()
  print(f"Indexed {page_count} pages -> {chunk_count} chunks from {len(files)} PDFs:")
  for name in files:
    print(f"  - {name}")
