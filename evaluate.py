"""Measure retrieval against data/eval_set.json. Run: python evaluate.py

Every query is written to be answerable from exactly one of the four PDFs. The score is
whether retrieval actually surfaces that PDF - which is also the regression test for the
bug this project had: the old ingest indexed only the first 30 pages, so acsbr-017.pdf and
p70-178.pdf were never searchable and every question about income or occupations failed
silently. Any return of that bug shows up here as those files scoring zero.

Makes NO LLM calls - only query embeddings - so it is fast and cheap. It does still need
NVIDIA_API_KEY, because the query has to be embedded with the same model as the index.
"""
import json
import sys
from collections import defaultdict

import config
from rag import retrieve


def evaluate(top_k=config.TOP_K):
  """Score every eval query. Returns (summary, per_file breakdown)."""
  config.require_key()
  with open(config.EVAL_SET, encoding="utf-8") as handle:
    cases = json.load(handle)
  hit1 = hitk = 0
  reciprocal = 0.0
  per_file = defaultdict(lambda: [0, 0])   # file -> [hits, total]
  misses = []
  for case in cases:
    docs = retrieve(case["query"], k=top_k)
    files = [d.metadata.get("source_file") for d in docs]
    position = files.index(case["expect"]) + 1 if case["expect"] in files else None
    per_file[case["expect"]][1] += 1
    if position:
      hitk += 1
      reciprocal += 1 / position
      per_file[case["expect"]][0] += 1
      if position == 1:
        hit1 += 1
    else:
      misses.append(case)
  total = len(cases)
  return ({"cases": total, "hit@1": hit1 / total, f"hit@{top_k}": hitk / total,
           "mrr": reciprocal / total}, per_file, misses)


def main():
  summary, per_file, misses = evaluate()
  top_k = config.TOP_K
  print(f"\n  Retrieval eval - {summary['cases']} queries, top_k={top_k}\n")
  print(f"    hit@1   {summary['hit@1']:>6.1%}")
  print(f"    hit@{top_k}   {summary[f'hit@{top_k}']:>6.1%}")
  print(f"    MRR     {summary['mrr']:.3f}\n")
  print("  per PDF (every file must be reachable - this is the docs[:30] regression check)")
  for name in sorted(per_file):
    hits, total = per_file[name]
    flag = "  <-- NOT REACHABLE" if hits == 0 else ""
    print(f"    {name:<20} {hits}/{total}{flag}")
  if misses:
    print(f"\n  Missed ({len(misses)}):")
    for case in misses:
      print(f"    - expected {case['expect']} for: {case['query'][:60]}...")
  print()
  unreachable = [n for n, (h, _) in per_file.items() if h == 0]
  # fail loudly if a whole PDF cannot be retrieved, or overall recall drops
  return 1 if unreachable or summary[f"hit@{top_k}"] < 0.8 else 0


if __name__ == "__main__":
  sys.exit(main())
