"""
Shadow AI Security & DLP Gateway — train / validation / test split
======================================================================

WHY WE SPLIT BY TEMPLATE, NOT BY ROW
--------------------------------------
Every row in dataset_clean.csv came from one of a small number of
sentence templates (recorded in the template_id column), just filled
with different fake names/emails/keys/etc. If rows from the SAME
template end up in both the training set and the test set, the model
can score well by recognizing the sentence shape it already memorized
— not by actually understanding the category. So this script makes
sure every row from a given template lands entirely in ONE split.

HOW THE SPLIT SIZE IS DECIDED
-------------------------------
The SRS asks for 70% train / 15% validation / 15% test. We apply that
ratio per LABEL (not globally) by splitting each label's templates
70/15/15, so that every label is represented in every split — not,
say, all of CONFIDENTIAL's templates landing in train by chance.
With only 15 templates per label, 70/15/15 can't divide evenly
(you can't split 15 cookies into perfectly even piles), so sizes are
rounded using the "largest remainder" method, which is the standard
fair way to round a set of shares so they still add up to the total.
"""

import csv
import random
from collections import defaultdict
from pathlib import Path

random.seed(42)

INPUT_PATH = Path(__file__).resolve().parent / "dataset_clean.csv"
OUT_DIR = Path(__file__).resolve().parent


def split_sizes(n, ratios=(0.70, 0.15, 0.15)):
    """Divide n items into len(ratios) integer shares that add up to exactly n."""
    raw = [n * r for r in ratios]
    sizes = [int(x) for x in raw]  # floor each share first
    remainder = n - sum(sizes)
    # give the leftover items to whichever shares had the largest fractional part
    order = sorted(range(len(ratios)), key=lambda i: raw[i] - sizes[i], reverse=True)
    for i in range(remainder):
        sizes[order[i]] += 1
    return sizes  # [train_count, val_count, test_count]


def main():
    with open(INPUT_PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # group rows by template, and templates by label
    rows_by_template = defaultdict(list)
    templates_by_label = defaultdict(set)
    for r in rows:
        rows_by_template[r["template_id"]].append(r)
        templates_by_label[r["label"]].add(r["template_id"])

    train_rows, val_rows, test_rows = [], [], []

    for label, template_ids in templates_by_label.items():
        template_ids = sorted(template_ids)  # deterministic order before shuffling
        random.shuffle(template_ids)
        n_train, n_val, n_test = split_sizes(len(template_ids))

        train_templates = template_ids[:n_train]
        val_templates = template_ids[n_train:n_train + n_val]
        test_templates = template_ids[n_train + n_val:]

        for t in train_templates:
            train_rows.extend(rows_by_template[t])
        for t in val_templates:
            val_rows.extend(rows_by_template[t])
        for t in test_templates:
            test_rows.extend(rows_by_template[t])

    # shuffle rows within each split so the CSV isn't grouped by template
    random.shuffle(train_rows)
    random.shuffle(val_rows)
    random.shuffle(test_rows)

    # sanity check: no template should ever appear in more than one split
    train_t = {r["template_id"] for r in train_rows}
    val_t = {r["template_id"] for r in val_rows}
    test_t = {r["template_id"] for r in test_rows}
    assert not (train_t & val_t), "LEAK: a template is in both train and val"
    assert not (train_t & test_t), "LEAK: a template is in both train and test"
    assert not (val_t & test_t), "LEAK: a template is in both val and test"

    fieldnames = ["id", "text", "label", "coarse_label", "template_id"]
    for name, split in [("train", train_rows), ("val", val_rows), ("test", test_rows)]:
        with open(OUT_DIR / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(split)

    total = len(train_rows) + len(val_rows) + len(test_rows)
    print("No template leaked across splits - confirmed.\n")
    print(f"{'split':<8}{'rows':>8}{'% of total':>12}")
    print("-" * 28)
    for name, split in [("train", train_rows), ("val", val_rows), ("test", test_rows)]:
        pct = 100 * len(split) / total
        print(f"{name:<8}{len(split):>8}{pct:>11.1f}%")

    print(f"\n{'label':<15}{'train':>7}{'val':>7}{'test':>7}")
    print("-" * 36)
    labels = sorted(templates_by_label.keys())
    for label in labels:
        tr = sum(1 for r in train_rows if r["label"] == label)
        va = sum(1 for r in val_rows if r["label"] == label)
        te = sum(1 for r in test_rows if r["label"] == label)
        print(f"{label:<15}{tr:>7}{va:>7}{te:>7}")


if __name__ == "__main__":
    main()
