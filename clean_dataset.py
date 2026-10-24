"""
Shadow AI Security & DLP Gateway — dataset cleaning step
==========================================================

WHY THIS EXISTS
----------------
Generating text from templates naturally produces some exact repeats
(the same sentence can come out twice if the random filler happened
to pick the same values). Duplicate rows don't teach a model anything
new, and if a duplicate ends up split across both the training set
and the test set later, the model's test score becomes artificially
inflated. So before we split the data, we remove exact repeats.

We also check for something more serious: the same TEXT appearing
twice with two DIFFERENT labels. That would mean either a template
bug or a genuinely ambiguous example, and it needs a human decision,
not an automatic fix — so this script reports it rather than
silently choosing one.
"""

import csv
from collections import Counter, defaultdict
from pathlib import Path

INPUT_PATH = Path(__file__).resolve().parent / "dataset_v1.csv"
OUTPUT_PATH = Path(__file__).resolve().parent / "dataset_clean.csv"


def main():
    with open(INPUT_PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    before_total = len(rows)
    before_counts = Counter(r["label"] for r in rows)

    # ---- check 1: same text, different labels (report only, don't guess) ----
    labels_per_text = defaultdict(set)
    for r in rows:
        labels_per_text[r["text"]].add(r["label"])

    conflicts = {text: labels for text, labels in labels_per_text.items() if len(labels) > 1}

    # ---- check 2: remove exact duplicate rows, keep the first occurrence ----
    seen_texts = set()
    clean_rows = []
    for r in rows:
        if r["text"] in seen_texts:
            continue
        seen_texts.add(r["text"])
        clean_rows.append(r)

    # re-number the id column so it stays sequential after removals
    for i, r in enumerate(clean_rows, start=1):
        r["id"] = i

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "text", "label", "coarse_label", "template_id"])
        writer.writeheader()
        writer.writerows(clean_rows)

    after_total = len(clean_rows)
    after_counts = Counter(r["label"] for r in clean_rows)

    print(f"Conflicting labels for identical text: {len(conflicts)}")
    if conflicts:
        for text, labels in list(conflicts.items())[:5]:
            print(f"  '{text[:60]}...' -> {labels}")

    print(f"\nRows before cleaning: {before_total}")
    print(f"Rows after cleaning:  {after_total}  (removed {before_total - after_total} exact duplicates)")
    print(f"\n{'label':<15}{'before':>8}{'after':>8}")
    print("-" * 31)
    for label in before_counts:
        print(f"{label:<15}{before_counts[label]:>8}{after_counts[label]:>8}")

    print(f"\nWrote cleaned dataset to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
