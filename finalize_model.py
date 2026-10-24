"""
Shadow AI Security & DLP Gateway — final model training + official test score
================================================================================
WHY RETRAIN ON train + val COMBINED
--------------------------------------
val.csv's job was to help choose between the three candidates. That
decision is made now (Naive Bayes), so val.csv has nothing left to
teach us about WHICH model to pick — holding it back from training
any longer would just be throwing away good data for no reason. We
fold it into training, then evaluate on test.csv exactly once.

WHY test.csv IS RUN EXACTLY ONCE, HERE, AND NEVER AGAIN
-----------------------------------------------------------
This run's numbers are what goes in the project report. If we ever
go back and retrain after seeing this score, test.csv stops being a
fair, unseen exam and becomes something we tuned against — and the
reported accuracy would no longer mean what it claims to mean.
"""

import time
from pathlib import Path

import pandas as pd
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import make_pipeline, make_union
from sklearn.naive_bayes import ComplementNB
from sklearn.metrics import classification_report, f1_score, ConfusionMatrixDisplay
import matplotlib.pyplot as plt

DATA_DIR = Path(__file__).resolve().parent
REPORT_DIR = DATA_DIR / "reports"
REPORT_DIR.mkdir(exist_ok=True)

train = pd.read_csv(DATA_DIR / "train.csv")
val = pd.read_csv(DATA_DIR / "val.csv")
test = pd.read_csv(DATA_DIR / "test.csv")

train_full = pd.concat([train, val], ignore_index=True)
print(f"Training on train+val combined: {len(train_full)} rows "
      f"({len(train)} from train, {len(val)} from val)")

X_tr, y_tr = train_full["text"], train_full["label"]
X_te, y_te = test["text"], test["label"]


def make_features():
    return make_union(
        TfidfVectorizer(analyzer="word", ngram_range=(1, 2), min_df=2, sublinear_tf=True,
                         token_pattern=r"(?u)\b\w+\b|[^\w\s]"),
        TfidfVectorizer(analyzer="char", ngram_range=(2, 5), min_df=2,
                         sublinear_tf=True, lowercase=False),
    )


pipe = make_pipeline(make_features(), ComplementNB())

t0 = time.perf_counter()
pipe.fit(X_tr, y_tr)
train_time = time.perf_counter() - t0

pred = pipe.predict(X_te)
macro_f1 = f1_score(y_te, pred, average="macro")

sample = list(X_te[:100])
t0 = time.perf_counter()
for s in sample:
    pipe.predict_proba([s])
per_text_ms = (time.perf_counter() - t0) / len(sample) * 1000

report = classification_report(y_te, pred, digits=3)

print(f"\n{'=' * 60}")
print("OFFICIAL TEST RESULT (naive_bayes, trained on train+val) - RUN ONCE")
print(f"macro-F1 = {macro_f1:.3f}  |  train_time = {train_time:.2f}s  |  {per_text_ms:.2f} ms/prediction")
print(f"{'=' * 60}")
print(report)

with open(REPORT_DIR / "FINAL_test_report.txt", "w") as f:
    f.write("OFFICIAL TEST RESULT (naive_bayes, trained on train+val)\n")
    f.write(f"macro-F1: {macro_f1:.4f}\ntrain_time_sec: {train_time:.3f}\n")
    f.write(f"ms_per_prediction: {per_text_ms:.3f}\n\n")
    f.write(report)

ConfusionMatrixDisplay.from_predictions(y_te, pred, xticks_rotation=45)
plt.title("Final model - TEST SET confusion matrix")
plt.tight_layout()
plt.savefig(REPORT_DIR / "FINAL_confusion_matrix.png", dpi=150)
plt.close()

joblib.dump(pipe, DATA_DIR / "final_model.joblib")
print(f"\nSaved final model to {DATA_DIR / 'final_model.joblib'}")
print(f"Saved official report + confusion matrix to {REPORT_DIR}")
