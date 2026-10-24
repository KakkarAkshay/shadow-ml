"""
Shadow AI Security & DLP Gateway — train & compare candidate models
======================================================================

WHAT THIS DOES
---------------
1. Turns each text into numbers using TF-IDF (word n-grams + character
   n-grams combined — see the explanation in the accompanying message).
2. Trains three candidate classifiers on train.csv:
     - Naive Bayes      (ComplementNB — a fast, simple baseline)
     - Logistic Regression
     - Linear SVM        (wrapped so it outputs honest confidence
                           scores, not just a bare yes/no)
3. Evaluates each one on val.csv: macro-F1, a full per-class report,
   a confusion matrix image, and prediction speed (ms per single
   text, since the real API will receive one prompt at a time).
4. Saves a report + confusion matrix + the trained model for each,
   plus one summary table comparing all three.

WHY macro-F1 TO COMPARE THEM
------------------------------
Macro-F1 treats every category equally, including the small ones.
If we used plain accuracy, a model could ignore PII entirely, still
nail accuracy by being right on the bigger categories, and we'd never
notice it was blind to PII. We don't pick a winner from this script —
you read the reports and decide, then tell me, and we run the winner
on test.csv exactly once at the end.
"""

import json
import time
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import make_pipeline, make_union
from sklearn.naive_bayes import ComplementNB
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import classification_report, f1_score, ConfusionMatrixDisplay

DATA_DIR = Path(__file__).resolve().parent
REPORT_DIR = DATA_DIR / "reports"
REPORT_DIR.mkdir(exist_ok=True)

train = pd.read_csv(DATA_DIR / "train.csv")
val = pd.read_csv(DATA_DIR / "val.csv")

X_tr, y_tr = train["text"], train["label"]
X_va, y_va = val["text"], val["label"]


def make_features():
    return make_union(
        TfidfVectorizer(analyzer="word", ngram_range=(1, 2), min_df=2, sublinear_tf=True,
                         token_pattern=r"(?u)\b\w+\b|[^\w\s]"),
        TfidfVectorizer(analyzer="char", ngram_range=(2, 5), min_df=2,
                         sublinear_tf=True, lowercase=False),
    )


MODELS = {
    "naive_bayes": ComplementNB(),
    "logreg": LogisticRegression(max_iter=1000, class_weight="balanced"),
    "linear_svm": CalibratedClassifierCV(LinearSVC(class_weight="balanced"), cv=3),
}


def main():
    summary = []

    for name, clf in MODELS.items():
        pipe = make_pipeline(make_features(), clf)

        t0 = time.perf_counter()
        pipe.fit(X_tr, y_tr)
        train_time = time.perf_counter() - t0

        pred = pipe.predict(X_va)
        macro_f1 = f1_score(y_va, pred, average="macro")

        # time single predictions, since the API will get one text at a time
        sample = list(X_va[:100])
        t0 = time.perf_counter()
        for s in sample:
            pipe.predict_proba([s])
        per_text_ms = (time.perf_counter() - t0) / len(sample) * 1000

        report = classification_report(y_va, pred, digits=3)
        header = (f"{name}  |  macro-F1={macro_f1:.3f}  |  "
                  f"train_time={train_time:.2f}s  |  {per_text_ms:.2f} ms/prediction")
        print(f"\n{'=' * len(header)}\n{header}\n{'=' * len(header)}")
        print(report)

        with open(REPORT_DIR / f"{name}_val_report.txt", "w") as f:
            f.write(header + "\n\n" + report)

        ConfusionMatrixDisplay.from_predictions(y_va, pred, xticks_rotation=45)
        plt.title(f"{name} — validation confusion matrix")
        plt.tight_layout()
        plt.savefig(REPORT_DIR / f"{name}_confusion_matrix.png", dpi=150)
        plt.close()

        joblib.dump(pipe, DATA_DIR / f"model_{name}.joblib")

        summary.append({
            "model": name,
            "macro_f1_val": round(macro_f1, 4),
            "train_time_sec": round(train_time, 3),
            "ms_per_prediction": round(per_text_ms, 3),
        })

    print("\n\nSUMMARY (validation set)")
    print(f"{'model':<15}{'macro-F1':>10}{'train (s)':>12}{'ms/predict':>12}")
    print("-" * 49)
    for r in summary:
        print(f"{r['model']:<15}{r['macro_f1_val']:>10.3f}{r['train_time_sec']:>12.2f}{r['ms_per_prediction']:>12.2f}")

    with open(REPORT_DIR / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\nSaved reports, confusion matrices, and trained models to {DATA_DIR}")


if __name__ == "__main__":
    main()
