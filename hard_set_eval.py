"""
Shadow AI Security & DLP Gateway — hard-set evaluation
======================================================================
The val.csv result was a 3-way tie at 100%, which just means the
template-based validation set was too easy to separate the models.
This script builds a small, hand-written set of harder examples —
natural phrasing the templates never produced, plus deliberate
"hard negatives" (text that LOOKS sensitive but isn't) — and checks
all three saved models against it. This is where real differences
between the models should actually show up.

This hard set is NOT the official test set. It's a sanity check to
help pick a model BEFORE we touch test.csv once, for real, at the end.
"""

import random
import string
from pathlib import Path

import joblib
import pandas as pd

random.seed(7)
DATA_DIR = Path(__file__).resolve().parent


def _luhn_checksum(number_str):
    digits = [int(d) for d in number_str]
    odd = digits[-1::-2]
    even = digits[-2::-2]
    total = sum(odd)
    for d in even:
        total += sum(divmod(d * 2, 10))
    return total % 10


def fake_card():
    prefix = random.choice(["4111", "4012", "5555"])
    partial = prefix + "".join(random.choices(string.digits, k=11))
    check = (10 - _luhn_checksum(partial + "0")) % 10
    full = partial + str(check)
    return " ".join(full[i:i + 4] for i in range(0, 16, 4))


HARD_SET = [
    # ---- SAFE: ordinary questions / chat, no templates reused ----
    ("What's the time complexity of binary search?", "SAFE"),
    ("How do I fix a bug where my loop never terminates?", "SAFE"),
    ("Our team retro is scheduled for next Tuesday afternoon.", "SAFE"),
    ("I think the migration script has an off-by-one error somewhere.", "SAFE"),
    ("Can you recommend a good book on system design interviews?", "SAFE"),
    ("What does 'confidential' mean in a legal contract?", "SAFE"),
    ("I'm nervous about presenting our project roadmap tomorrow.", "SAFE"),
    ("Could you help me understand REST vs GraphQL?", "SAFE"),
    ("Why does Python's garbage collector sometimes not free memory immediately?", "SAFE"),
    ("Explain what a race condition is in multithreaded programming.", "SAFE"),
    ("We had a great turnout at the product demo yesterday, thanks everyone.", "SAFE"),
    ("Quarterly all-hands is moved to 3 PM this Friday.", "SAFE"),
    ("Can you review the pull request before the demo?", "SAFE"),

    # ---- SAFE hard negatives: look sensitive, aren't ----
    ("The order number for my package is 48213.", "SAFE"),
    ("Flight AI-202 departs from gate 14B at 6:45.", "SAFE"),
    ("The invoice total came to 4,111 rupees after tax.", "SAFE"),
    ("Reference ticket number is TCK-88291, raised yesterday.", "SAFE"),
    ("My friend's birthday is next week, should I get him a gift card?", "SAFE"),
    ("Here's the secret.", "SAFE"),

    # ---- SOURCE_CODE: different snippets than the templates used ----
    ("while (!done) { process(queue.pop()); }", "SOURCE_CODE"),
    ("SELECT * FROM users WHERE last_login IS NULL;", "SOURCE_CODE"),
    ("def reverse_string(s): return s[::-1]", "SOURCE_CODE"),
    ("<button onClick={() => setOpen(!open)}>Toggle</button>", "SOURCE_CODE"),
    ("import numpy as np\narr = np.array([1, 2, 3])", "SOURCE_CODE"),

    # ---- CONFIDENTIAL: no "confidential/internal" keyword, contextual only ----
    ("Don't mention this outside the team, but we're cutting the marketing budget 40% next quarter.", "CONFIDENTIAL"),
    ("Leadership decided this morning to delay the layoffs announcement until after the board meeting.", "CONFIDENTIAL"),
    ("The acquisition offer came in at 2.3x revenue, keep that between us for now.", "CONFIDENTIAL"),
    ("We're planning to undercut their pricing by 15% before the public announcement next month.", "CONFIDENTIAL"),
    ("The new product codename is Thunderbird, don't post that in the public Slack channel.", "CONFIDENTIAL"),
    ("The merger talks are off the record until Monday's press release, don't repeat this.", "CONFIDENTIAL"),

    # ---- EMAIL / PHONE: natural phrasing ----
    ("Shoot me a note whenever, I'm at r.verma88@example.com", "EMAIL"),
    ("Here's where to reach the ops lead: ops-lead@example.org", "EMAIL"),
    ("Ring me anytime, it's +91-9876543210.", "PHONE"),
    ("Front desk number is 555-0147 if anyone asks.", "PHONE"),

    # ---- API_KEY / PASSWORD: no "key"/"password" keyword in some ----
    ("export STRIPE_KEY=sk_live_51Hc9f2K8pQmZ9L2x", "API_KEY"),
    ("swap in AKIA3F9QXZ7HLP2MK8R4 before you redeploy", "API_KEY"),
    ("just use guestWifi2024! to get online", "PASSWORD"),
    ("if it still doesn't let you in try Falcon&271 one more time", "PASSWORD"),

    # ---- PAYMENT_CARD: valid Luhn numbers, generated fresh ----
    (f"charge it to {fake_card()} please", "PAYMENT_CARD"),
    (f"card on file is {fake_card()}", "PAYMENT_CARD"),

    # ---- PII ----
    ("Please pull up the file for S. Kapoor, record number 7731 4420 9981.", "PII"),
    ("Candidate Rohan Mehta, born 14-03-1998, passport W2290134.", "PII"),
]


def main():
    df = pd.DataFrame(HARD_SET, columns=["text", "label"])
    df.to_csv(DATA_DIR / "hard_set.csv", index=False)

    for name in ["naive_bayes", "logreg", "linear_svm"]:
        model = joblib.load(DATA_DIR / f"model_{name}.joblib")
        pred = model.predict(df["text"])
        correct = (pred == df["label"]).sum()
        total = len(df)

        print(f"\n{'=' * 50}\n{name}: {correct}/{total} correct ({100 * correct / total:.1f}%)\n{'=' * 50}")
        mistakes = df.copy()
        mistakes["predicted"] = pred
        mistakes = mistakes[mistakes["label"] != mistakes["predicted"]]
        if len(mistakes) == 0:
            print("No mistakes.")
        else:
            for _, row in mistakes.iterrows():
                print(f"  '{row['text'][:55]}...' -> true={row['label']:<13} predicted={row['predicted']}")


if __name__ == "__main__":
    main()
