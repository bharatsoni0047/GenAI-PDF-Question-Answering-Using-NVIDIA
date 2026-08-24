# STAR — Ask Your PDFs

The problem, the decisions and what came out of them. See [README.md](README.md) to run it.

---

## Situation

A document question-answering system is easy to build and very hard to trust. The pattern
is well known — read the files, cut them up, find the relevant pieces, hand them to a
language model — and a working version can be assembled in an afternoon.

The difficulty is that **when it goes wrong, it does not look wrong.** A retrieval system
that quietly fails to search half its documents still returns a confident, fluent, well
formatted answer. There is no error, no empty result, no warning. The user has no way of
telling the difference between "the system read everything and this is the answer" and "the
system read a third of it and this is the closest thing it found".

This project started as a working prototype with exactly that failure in it, and I did not
find it by reading the code. I found it by trying to measure the code.

---

## Task

Turn a demo into something whose answers can be checked, with three requirements:

| Requirement | Why |
|---|---|
| **Every page must actually be searched** | A silently incomplete index is worse than no index — it produces confident answers from partial data. |
| **Every answer must be traceable** | A fact with no source cannot be verified, and an unverifiable answer from a document system is worthless. |
| **The coverage must be checked automatically** | Finding this bug once is luck. Catching it every time is engineering. |

---

## Action

### 1. Found a bug that was invisible from the code

The original ingestion looked entirely reasonable:

```python
text_splitter.split_documents(st.session_state.docs[:30])
```

Reading that line, `[:30]` looks like a sensible guard against a runaway document. It is
not, because the loader returns **one document per page**, not per file. On this corpus of
63 pages it indexed the first 30 and discarded the rest:

| Document | Pages | What actually happened |
|---|---|---|
| Health insurance | 18 | fully indexed |
| Poverty report | 15 | only 12 of 15 |
| Household income | 9 | **never indexed** |
| Jobs and earnings | 21 | **never indexed** |

**52% of the corpus was unreachable**, including two documents in their entirety. Every
question about household income or occupations was unanswerable, and the app answered them
anyway from unrelated text.

The lesson I took: this was not a coding mistake, it was a **missing feedback loop**. The
code was readable and the bug was in plain sight. Nothing in the system was in a position
to notice.

### 2. Built the check before fixing the bug

Rather than fix the line and move on, I wrote the measurement first: sixteen questions, each
answerable from exactly one document, phrased differently from the source text so it tests
understanding rather than word matching.

The important design choice is what it reports. An overall accuracy score would have shown
around 50% and been easy to shrug off as "needs tuning". Instead it reports **per document**:

```
Health insurance   4/4
Poverty report     3/3
Household income   4/4      <- would have read 0/4 before the fix
Jobs and earnings  5/5      <- would have read 0/5 before the fix
```

A document scoring zero is unmissable, and the script exits non-zero so it can gate a build.
That turns a one-off discovery into a permanent regression test.

It makes no chat-model calls, so it runs in seconds and costs almost nothing — which is what
makes it something you would actually run.

### 3. Fixed retrieval running twice

The original invoked the retriever inside the answer chain, then invoked it **again** to
populate the "sources" panel. Two consequences: every question paid for retrieval twice,
and the excerpts shown to the user were not guaranteed to be the excerpts the answer was
written from.

That second point is the serious one. A sources panel that might not match the answer is
worse than no sources panel, because it looks like verification while providing none. Now
retrieval happens once and the same documents flow to both the model and the display.

### 4. Made citations possible at all

Chunks originally carried no metadata, so even a correct answer could not say where it came
from. Each chunk now stores its file name and page number, the prompt requires citations in
`[file p.N]` form, and the retrieved excerpts are labelled the same way so the model has
something to cite.

### 5. Moved indexing out of the interface

Indexing was triggered by a button inside the Streamlit app. That made it impossible to run
in a script, impossible to test, and easy to forget. It became a standalone step that the
eval also uses, so the app and the measurement exercise the same code path.

### 6. General cleanup

Added a `.gitignore` — the secrets file and the vector store were both committable. Removed
a leftover `print("hEllo")` and an unused import, dropped two packages from requirements
that nothing imported, and deleted a stray demo file containing a hardcoded key
placeholder.

---

## Result

| Outcome | Detail |
|---|---|
| **Full coverage** | 63 pages, 301 searchable pieces, all four documents reachable |
| **Verifiable answers** | Every answer cites file and page; the sources shown are the ones used |
| **Automatic regression check** | Per-document reporting, exits non-zero if any becomes unreachable |
| **Half the retrieval cost** | One search per question instead of two |
| **A repository that is safe to clone** | Secrets and generated data no longer committable |

### What I would tell an interviewer

This project is my example of **why a measurement is worth more than a code review**.

The bug was one expression, in plain sight, in a file of under a hundred lines. It survived
because reading `docs[:30]` does not tell you that `docs` is pages rather than files —
that only becomes visible when something tries to find a fact and cannot. I did not catch
it by being careful. I caught it because I decided to build an eval harness, and the harness
had no choice but to report it.

That is also why the check reports per document rather than as a single number. A 50%
average invites tuning. A document showing zero is unambiguous — it says *this file is not
in the system*, which is a completely different problem with a completely different fix.

The habit I would carry forward: **when a system's failure mode is silence, the first thing
to build is the thing that makes it speak.**

### What I would do next

1. **Measure the writing, not just the finding.** Coverage proves the right document is
   retrieved; it says nothing about whether the answer drawn from it is correct.
2. **Add keyword search alongside meaning-based search** — but measure it before keeping
   it. On a sibling project I built exactly that, measured it, and it made things worse.
3. **Handle scanned PDFs.** Text is read directly, so image-only pages come out empty and
   silently contribute nothing — the same class of invisible failure as the original bug.
4. **Show a confidence signal in the interface** when the best match is weak, rather than
   answering with the same certainty regardless.
