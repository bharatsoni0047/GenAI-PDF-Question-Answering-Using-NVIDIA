# PDF Question Answering — NVIDIA NIM + Chroma

Ask questions in plain English about a folder of PDFs and get answers **grounded in the
documents, with the file and page cited**.

The corpus here is four US Census Bureau reports (63 pages) on health insurance coverage,
poverty, household income, and occupations and earnings. Point `PDF_DIR` at your own folder
to change the domain.

```
python ingest.py            # index every page of every PDF, once
streamlit run app.py        # ask questions
python evaluate.py          # score retrieval
```

## How it works

```
pdfs/*.pdf ──▶ ingest.py ──▶ Chroma (persisted)
               every page,        │
               1000-char chunks,  │
               tagged with        │
               file + page        │
                                  ▼
   question ──▶ retrieve top 4 ──▶ LLM ──▶ answer with [file p.N] citations
                                    │
                                    └── the SAME 4 excerpts shown in the UI
```

| Component | Choice |
|---|---|
| Embeddings | NVIDIA `nv-embed-v1` |
| LLM | `deepseek-ai/deepseek-v3.2` via ChatNVIDIA |
| Vector store | Chroma, persisted to disk |
| UI | Streamlit |

## Retrieval is measured, not assumed

`python evaluate.py` scores 16 questions, each answerable from exactly one PDF. It makes
**no LLM calls** — only query embeddings — so it is fast and cheap.

It also prints a per-PDF breakdown, and that is the important part:

```
  per PDF (every file must be reachable)
    acsbr-015.pdf        4/4
    acsbr-016.pdf        3/3
    acsbr-017.pdf        4/4
    p70-178.pdf          5/5
```

A file scoring `0/n` means it is not in the index at all, and the script exits non-zero —
which is a regression test for the bug described below.

## The bug this project had

The old ingest ran inside a Streamlit button handler and did this:

```python
text_splitter.split_documents(st.session_state.docs[:30])
```

`PyPDFDirectoryLoader` returns **one document per page**. This corpus is 63 pages, so
`[:30]` silently discarded 52% of it:

| PDF | Pages | Old behaviour |
|---|---|---|
| acsbr-015.pdf | 18 | fully indexed |
| acsbr-016.pdf | 15 | only 12 of 15 |
| **acsbr-017.pdf** | 9 | **never indexed** |
| **p70-178.pdf** | 21 | **never indexed** |

Every question about household income or occupations was unanswerable, and nothing in the
UI said so — the app simply answered from whatever unrelated text ranked highest. Indexing
now covers all 63 pages (301 chunks), and `evaluate.py` fails loudly if any PDF stops being
reachable.

## Also fixed

- **Retrieval ran twice per question** — once inside the chain, once again to populate the
  "similarity search" expander. The two searches could return different excerpts, so the
  sources shown were not necessarily the sources used. Now it retrieves once and passes the
  documents through.
- **No citations.** Chunks carried no file or page metadata, so an answer could not be traced
  back. Every chunk is now tagged and the prompt requires `[file p.N]` citations.
- **Indexing lived in the UI.** Moved to `ingest.py`, so the eval and the app share one code
  path and re-indexing is not a button click.
- **No `.gitignore`** — `.env` and `chroma_db/` could have been committed. Added.
- Removed `faiss-cpu` and `openai` from requirements (imported nowhere), plus a leftover
  `print("hEllo")` and an unused FAISS import.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env        # add your NVIDIA_API_KEY - free at build.nvidia.com

python ingest.py            # ~1 min, writes chroma_db/
streamlit run app.py
```

## Project structure

```
config.py       every setting, one place
ingest.py       PDFs -> pages -> chunks -> Chroma (run once)
rag.py          retrieval + prompt + answer, shared by the UI and the eval
app.py          Streamlit UI
evaluate.py     scores retrieval, no LLM calls
data/           eval_set.json - 16 questions with the PDF each should hit
pdfs/           the source documents
```

## Known limits

- **Retrieval is vector-only.** No keyword search or reranking. Worth adding if the corpus
  grows — but measure it with `evaluate.py` first rather than assuming it helps.
- **`evaluate.py` scores retrieval, not answer quality.** It checks the right PDF is found,
  not that the generated answer is correct.
- **The eval needs an API key**, because the query must be embedded with the same model as
  the index. It makes no LLM calls, so it is still cheap.
