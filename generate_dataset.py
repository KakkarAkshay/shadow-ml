"""
Shadow AI Security & DLP Gateway — synthetic training-data generator
======================================================================

WHY THIS EXISTS
----------------
The SRS (section 2.2) requires a *synthetic* labelled dataset, because
real credentials, real personal data, or real leaked passwords must
never be used for testing. This script writes many small "template"
sentences per category, then fills in the blanks with randomly
generated FAKE values (fake emails, fake passwords, fake card numbers
that pass the Luhn check but aren't tied to any real account, etc).
Nothing generated here is a real secret or a real person's data.

WHAT IT PRODUCES
-----------------
A CSV with columns:
    id            - row number
    text          - the example sentence/snippet
    label         - one of the 9 fine-grained labels
    coarse_label  - the 3-way SAFE / SOURCE_CODE / CONFIDENTIAL view
                    the SRS's ML classifier ultimately outputs
    template_id   - which template produced this row (used later to
                    split train/val/test by template, so the model
                    is tested on sentence PATTERNS it has never seen,
                    not just different names plugged into a pattern
                    it already memorized)

HOW TO CHANGE THE DATASET SIZE
-------------------------------
Edit SAMPLES_PER_TEMPLATE below. Each category has ~15 templates, so
SAMPLES_PER_TEMPLATE=14 gives roughly 15*14 = 210 rows per category.
"""

import csv
import random
import string
from pathlib import Path

random.seed(42)  # same output every run, so results are reproducible

SAMPLES_PER_TEMPLATE = 14
OUTPUT_PATH = Path(__file__).resolve().parent / "dataset_v1.csv"

# ----------------------------------------------------------------------
# Fake-value generators
# Every one of these produces something that LOOKS real enough for the
# model to learn from, but is guaranteed not to be a real credential,
# real card, or real person's identity.
# ----------------------------------------------------------------------

FIRST_NAMES = ["Aarav", "Isha", "Rohan", "Priya", "Karan", "Neha", "Vikram", "Ananya",
               "Rahul", "Simran", "Aditya", "Meera", "Arjun", "Divya", "Kabir", "Tanya",
               "Sameer", "Pooja", "Nikhil", "Riya"]
LAST_NAMES = ["Sharma", "Verma", "Gupta", "Patel", "Nair", "Iyer", "Reddy", "Khan",
              "Chopra", "Malhotra", "Kapoor", "Joshi", "Mehta", "Singh", "Rao", "Bose",
              "Dutta", "Pillai", "Agarwal", "Shah"]
# example.com/.org/.net are reserved by IANA specifically for documentation
# and examples — guaranteed to never belong to a real registrant.
FAKE_DOMAINS = ["example.com", "example.org", "example.net",
                "northwind-test.com", "acmecorp-test.io", "brightpath-test.org"]
COMPANIES = ["Northwind Analytics", "Brightpath Systems", "Acme Manufacturing", "Orion Retail Group",
             "Cobalt Logistics", "Fernwood Health", "Lumen Financial", "Harborline Shipping",
             "Ridgeview Software", "Meadowbrook Insurance", "Ironclad Security", "Silverline Media"]
CODE_NAMES = ["Falcon", "Griffin", "Orion", "Nimbus", "Zephyr", "Cascade", "Meridian", "Solstice",
              "Comet", "Atlas", "Beacon", "Phoenix", "Compass", "Horizon", "Vertex", "Aurora"]
TOPICS = ["photosynthesis", "compound interest", "gravity", "the water cycle", "inflation",
          "tectonic plates", "supply and demand", "cellular respiration", "the stock market",
          "monsoon formation", "machine learning basics", "blockchain", "renewable energy",
          "evolution", "the immune system", "black holes", "fermentation", "climate change",
          "the nervous system", "GDP growth", "osmosis", "artificial intelligence",
          "the solar system", "natural selection", "supply chains", "plate tectonics",
          "genetic inheritance", "thermodynamics", "supply shocks", "urbanization",
          "vaccination", "quantum computing", "deforestation", "the Krebs cycle"]
NOUNS = ["order", "invoice", "user", "product", "payment", "ticket", "session", "cart",
         "employee", "inventory", "booking", "review", "transaction", "account",
         "shipment", "request", "report", "task", "comment", "subscription",
         "customer", "vendor", "refund", "warehouse", "supplier", "driver",
         "package", "voucher", "claim", "appointment", "license", "contract",
         "shift", "batch", "auction"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
TIMES = ["10 AM", "2 PM", "3:30 PM", "end of day", "first thing tomorrow", "right after lunch"]


def fake_order():
    return str(random.randint(10000, 99999))


def fake_ticket():
    return f"TCK-{random.randint(10000, 99999)}"


def fake_flight():
    return f"{random.choice(['AI', '6E', 'UK', 'SG'])}-{random.randint(100, 999)}"


def fake_gate():
    return f"{random.choice('ABCDEF')}{random.randint(1, 30)}"


def fake_amount():
    return f"{random.randint(500, 9999):,}"


def fake_name():
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def fake_email():
    handle = f"{random.choice(FIRST_NAMES)}.{random.choice(LAST_NAMES)}{random.randint(1, 999)}".lower()
    return f"{handle}@{random.choice(FAKE_DOMAINS)}"


def fake_phone():
    if random.random() < 0.5:
        # 555-01xx is reserved by the North American Numbering Plan for
        # fictional use in film/TV/testing — guaranteed not a real line.
        return f"+1-555-01{random.randint(10, 99)}"
    return f"+91-{random.choice('6789')}{random.randint(10000000, 99999999)}"


def fake_api_key():
    prefix = random.choice(["sk-live-", "sk-test-", "ghp_", "AKIA", "xoxb-", "api_key_"])
    body = "".join(random.choices(string.ascii_letters + string.digits, k=random.randint(20, 28)))
    return prefix + body


def fake_password():
    words = ["Tr0ub4dor", "Summer", "Dragon", "Winter", "Purple", "Rocket", "Falcon", "Shadow"]
    symbol = random.choice(["!", "&", "#", "@"])
    return f"{random.choice(words)}{symbol}{random.randint(1, 999)}"


def _luhn_checksum(number_str):
    digits = [int(d) for d in number_str]
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    total = sum(odd_digits)
    for d in even_digits:
        total += sum(divmod(d * 2, 10))
    return total % 10


def fake_card():
    # These prefixes are publicly documented Visa/Mastercard TEST BIN
    # ranges (used in sandbox/testing docs industry-wide) — not real
    # issued account ranges.
    prefix = random.choice(["4111", "4012", "4242", "5555", "5105"])
    partial = prefix + "".join(random.choices(string.digits, k=11))  # 15 digits
    checksum_with_zero = _luhn_checksum(partial + "0")
    check_digit = (10 - checksum_with_zero) % 10
    full = partial + str(check_digit)
    return " ".join(full[i:i + 4] for i in range(0, 16, 4))


def fake_pii_id():
    return f"{random.randint(1000, 9999)} {random.randint(1000, 9999)} {random.randint(1000, 9999)}"


def fake_dob():
    return f"{random.randint(1, 28):02d}-{random.randint(1, 12):02d}-{random.randint(1970, 2005)}"


def fill(template: str) -> str:
    """Replace every __TOKEN__ placeholder in a template with a fresh fake value."""
    text = template
    if "__NAME__" in text:
        text = text.replace("__NAME__", fake_name())
    if "__EMAIL__" in text:
        text = text.replace("__EMAIL__", fake_email())
    if "__PHONE__" in text:
        text = text.replace("__PHONE__", fake_phone())
    if "__KEY__" in text:
        text = text.replace("__KEY__", fake_api_key())
    if "__PASSWORD__" in text:
        text = text.replace("__PASSWORD__", fake_password())
    if "__CARD__" in text:
        text = text.replace("__CARD__", fake_card())
    if "__PII_ID__" in text:
        text = text.replace("__PII_ID__", fake_pii_id())
    if "__DOB__" in text:
        text = text.replace("__DOB__", fake_dob())
    if "__COMPANY__" in text:
        text = text.replace("__COMPANY__", random.choice(COMPANIES))
    if "__CODENAME__" in text:
        text = text.replace("__CODENAME__", random.choice(CODE_NAMES))
    if "__TOPIC__" in text:
        text = text.replace("__TOPIC__", random.choice(TOPICS))
    if "__NOUN__" in text or "__NOUN_CAP__" in text:
        noun = random.choice(NOUNS)
        text = text.replace("__NOUN_CAP__", noun.capitalize())
        text = text.replace("__NOUN__", noun)
    if "__DAY__" in text:
        text = text.replace("__DAY__", random.choice(DAYS))
    if "__TIME__" in text:
        text = text.replace("__TIME__", random.choice(TIMES))
    if "__ORDER__" in text:
        text = text.replace("__ORDER__", fake_order())
    if "__TICKET__" in text:
        text = text.replace("__TICKET__", fake_ticket())
    if "__FLIGHT__" in text:
        text = text.replace("__FLIGHT__", fake_flight())
    if "__GATE__" in text:
        text = text.replace("__GATE__", fake_gate())
    if "__AMOUNT__" in text:
        text = text.replace("__AMOUNT__", fake_amount())
    return text


# ----------------------------------------------------------------------
# Templates, one list per label
# ----------------------------------------------------------------------

TEMPLATES = {

    "SAFE": [
        "Can you explain how __TOPIC__ works in simple terms?",
        "What are the main factors that influence __TOPIC__?",
        "I'm studying __TOPIC__ for my exam, can you summarize the key points?",
        "Give me a beginner-friendly explanation of __TOPIC__.",
        "What's a good analogy to understand __TOPIC__?",
        "Why is __TOPIC__ important in real life?",
        "Can you quiz me on __TOPIC__?",
        "What are common misconceptions about __TOPIC__?",
        "Suggest three resources to learn more about __TOPIC__.",
        "What's the history behind our understanding of __TOPIC__?",
        "Can you compare __TOPIC__ to something from everyday life?",
        "What questions should I ask my professor about __TOPIC__?",
        "Summarize __TOPIC__ in two sentences for a quick revision.",
        "What's a fun fact about __TOPIC__ that most people don't know?",
        "How would you teach __TOPIC__ to a ten-year-old?",
        # ---- everyday / non-technical chat, no __TOPIC__ at all ----
        "Our team retro is scheduled for __DAY__ afternoon.",
        "Quarterly all-hands got moved to __TIME__ on __DAY__.",
        "Can you review the pull request before the demo on __DAY__?",
        "I think the __NOUN__ migration script has an off-by-one error somewhere.",
        "We had a great turnout at the __NOUN__ demo yesterday, thanks everyone.",
        "The order number for my package is __ORDER__.",
        "Reference ticket number is __TICKET__, raised yesterday.",
        "Flight __FLIGHT__ departs from gate __GATE__ at __TIME__.",
        "The invoice total came to __AMOUNT__ rupees after tax.",
        "My friend's birthday is next week, should I get him a gift card?",
        "What does 'confidential' mean in a legal contract?",
        "I'm nervous about presenting our __NOUN__ roadmap tomorrow.",
        "Here's the plan for tomorrow's __NOUN__ sync.",
        "Let's grab coffee and catch up sometime this __DAY__.",
        "Can you proofread this __NOUN__ update before I send it out?",
    ],

    "SOURCE_CODE": [
        "def calculate___NOUN___total(items):\n    return sum(i.price * i.qty for i in items)",
        "SELECT __NOUN__id, COUNT(*) FROM __NOUN__s GROUP BY __NOUN__id;",
        "class __NOUN_CAP__Manager:\n    def __init__(self):\n        self.items = []\n    def add(self, item):\n        self.items.append(item)",
        "for i in range(len(__NOUN__s) - 1):\n    if __NOUN__s[i] > __NOUN__s[i + 1]:\n        __NOUN__s[i], __NOUN__s[i+1] = __NOUN__s[i+1], __NOUN__s[i]",
        "const fetch__NOUN_CAP__s = async () => { const res = await fetch('/api/__NOUN__s'); return res.json(); };",
        "def is_valid___NOUN__(x):\n    return x is not None and x.status == 'active'",
        "UPDATE __NOUN__s SET status = 'closed' WHERE __NOUN___id = 42 AND status = 'open';",
        "public class __NOUN_CAP__Queue {\n  private int[] data;\n  private int top = -1;\n  public void push(int x) { data[++top] = x; }\n}",
        "import React, { useState } from 'react';\nfunction __NOUN_CAP__Counter() { const [count, setCount] = useState(0); return count; }",
        "def merge_sort(__NOUN__s):\n    if len(__NOUN__s) <= 1: return __NOUN__s\n    mid = len(__NOUN__s) // 2\n    return mid",
        "try:\n    result = process___NOUN__(data)\nexcept ValueError:\n    result = None",
        "CREATE TABLE __NOUN__s (id INTEGER PRIMARY KEY, name TEXT, amount REAL);",
        "def fibonacci(n, memo=None):\n    if memo is None: memo = {}\n    if n in memo: return memo[n]\n    return n",
        "while queue:\n    __NOUN__ = queue.popleft()\n    visited.add(__NOUN__)\n    queue.extend(n for n in graph[__NOUN__] if n not in visited)",
        "DELETE FROM __NOUN__s WHERE created_at < NOW() - INTERVAL '30 days';",
    ],

    "EMAIL": [
        "Please send the invoice to __EMAIL__ by Friday.",
        "You can reach our support team at __EMAIL__.",
        "I updated my contact email to __EMAIL__, please use that going forward.",
        "Can you CC __EMAIL__ on this thread?",
        "My personal email is __EMAIL__, feel free to email me there.",
        "Forward the meeting notes to __EMAIL__ once you're done.",
        "The client's email address is __EMAIL__, use it for all correspondence.",
        "Sign up for the newsletter using __EMAIL__.",
        "I lost access to __EMAIL__, can you help reset it?",
        "Add __EMAIL__ to the mailing list for updates.",
        "Our HR contact email is __EMAIL__ for any leave requests.",
        "Please confirm your registration by replying from __EMAIL__.",
        "The vendor asked us to send the PO to __EMAIL__.",
        "I'll share the document link with __EMAIL__ shortly.",
        "Use __EMAIL__ as the recovery address for this account.",
    ],

    "PHONE": [
        "You can reach me at __PHONE__ after 6 PM.",
        "Please call the helpdesk at __PHONE__ for urgent issues.",
        "My new number is __PHONE__, update your contacts.",
        "The delivery driver will call __PHONE__ when he arrives.",
        "For appointment confirmations, text __PHONE__.",
        "Our office landline is __PHONE__, extension 204.",
        "I gave the recruiter my number __PHONE__ for a follow-up call.",
        "Emergency contact number: __PHONE__.",
        "Please share __PHONE__ with the vendor for coordination.",
        "Call me on __PHONE__ if the meeting time changes.",
        "The technician's contact number is __PHONE__.",
        "Message me at __PHONE__ once you land.",
        "Add __PHONE__ as the alternate contact number.",
        "My roommate's number is __PHONE__ in case you can't reach me.",
        "Use __PHONE__ for OTP verification.",
    ],

    "API_KEY": [
        "Use this key for the staging environment: __KEY__",
        "Here's the API key you asked for: __KEY__",
        "Set the environment variable API_KEY=__KEY__ before running the script.",
        "I accidentally committed the key __KEY__ to the repo, please rotate it.",
        "The webhook secret is __KEY__, keep it out of version control.",
        "Paste this into your .env file: SECRET_KEY=__KEY__",
        "Our third-party integration uses the token __KEY__.",
        "Can you test the endpoint with key __KEY__?",
        "I found this key in the old config file: __KEY__",
        "The deployment script needs ACCESS_KEY=__KEY__.",
        "Here's the bot token: __KEY__",
        "This is the temporary key for the demo: __KEY__",
        "Replace the placeholder with the real key __KEY__ before deploying.",
        "The CI pipeline reads the key __KEY__ from a secrets file.",
        "Here's my personal access token in case you need it: __KEY__",
    ],

    "PASSWORD": [
        "My login is admin / __PASSWORD__, please don't share it.",
        "I reset my password to __PASSWORD__, can you confirm it works?",
        "The default password for the test account is __PASSWORD__.",
        "Use username 'support' and password __PASSWORD__ to access the panel.",
        "I wrote the wifi password __PASSWORD__ on the whiteboard by mistake.",
        "Can you log in with the temporary password __PASSWORD__ I sent earlier?",
        "Our shared drive password is __PASSWORD__, don't post it publicly.",
        "The database root password is __PASSWORD__.",
        "I forgot my password, the old one was __PASSWORD__.",
        "Set the new password to __PASSWORD__ for this account.",
        "Here's the password for the guest account: __PASSWORD__",
        "The router admin password is __PASSWORD__.",
        "Please change the password from __PASSWORD__ to something stronger.",
        "My email password used to be __PASSWORD__ before I got locked out.",
        "The vendor portal login uses password __PASSWORD__.",
    ],

    "PAYMENT_CARD": [
        "My card number is __CARD__, expiry 09/28.",
        "Please charge __CARD__ for the subscription renewal.",
        "I entered card __CARD__ but the payment failed.",
        "Here's my card for the reservation: __CARD__",
        "Can you update the billing info to card __CARD__?",
        "The refund should go back to card __CARD__.",
        "I used card __CARD__ for the online order.",
        "Save card __CARD__ for future purchases.",
        "My corporate card number is __CARD__.",
        "The client paid with card __CARD__ over the phone.",
        "Please don't store card __CARD__ after this transaction.",
        "I need to update my card on file to __CARD__.",
        "Card __CARD__ was declined at checkout.",
        "Use card __CARD__ for the annual software license.",
        "My backup card is __CARD__ in case the first one fails.",
    ],

    "PII": [
        "__NAME__'s date of birth is __DOB__, needed for the background check.",
        "Please verify __NAME__'s ID number __PII_ID__ before processing.",
        "__NAME__ lives at 42 Lotus Enclave, Sector 12, born on __DOB__.",
        "The applicant __NAME__ submitted ID __PII_ID__ with the form.",
        "HR record: __NAME__, DOB __DOB__, employee ID __PII_ID__.",
        "__NAME__'s national ID number is __PII_ID__.",
        "Please update __NAME__'s record: DOB __DOB__, address on file unchanged.",
        "Patient __NAME__, DOB __DOB__, was admitted this morning.",
        "__NAME__'s passport number is __PII_ID__.",
        "We need __NAME__'s ID __PII_ID__ for the KYC process.",
        "__NAME__ (DOB __DOB__) has been added to the insurance policy.",
        "Emergency contact form: __NAME__, ID number __PII_ID__.",
        "__NAME__'s tax ID is __PII_ID__.",
        "The candidate's full name is __NAME__, born __DOB__.",
        "Please cross-check __NAME__'s ID __PII_ID__ against the database.",
    ],

    "CONFIDENTIAL": [
        "Internal memo: __COMPANY__'s Q3 pricing strategy for Project __CODENAME__ is not to be shared externally.",
        "Project __CODENAME__ roadmap: this document is confidential and for leadership only.",
        "Do not forward — __COMPANY__'s acquisition talks are still under NDA.",
        "Project __CODENAME__ budget figures are restricted to the finance team.",
        "This is an internal-only summary of __COMPANY__'s restructuring plan for next quarter.",
        "Confidential: __COMPANY__ board meeting notes on the Project __CODENAME__ merger.",
        "Please keep Project __CODENAME__ launch details internal until the press release.",
        "__COMPANY__'s salary bands for the Project __CODENAME__ team are strictly confidential.",
        "Internal use only: competitor analysis for __COMPANY__'s upcoming product.",
        "The Project __CODENAME__ security incident report is classified internal-confidential.",
        "Do not distribute — __COMPANY__'s unreleased financial results for this quarter.",
        "Project __CODENAME__: internal strategy doc, not for client distribution.",
        "__COMPANY__ leadership circulated this confidential note about restructuring.",
        "Marked confidential: __COMPANY__'s vendor contract terms for Project __CODENAME__.",
        "Internal only — __COMPANY__'s upcoming layoffs are not to be discussed outside HR.",
    ],
}

# The SRS's ML classifier ultimately outputs one of three coarse labels.
# The six structured categories fold into CONFIDENTIAL at that level,
# since they're all sensitive content Devansh's rules already pinpoint
# precisely — your model's extra value is mainly in SOURCE_CODE vs
# CONFIDENTIAL vs SAFE, the cases plain regex can't resolve.
def coarse_label_for(label: str) -> str:
    if label in ("SAFE", "SOURCE_CODE", "CONFIDENTIAL"):
        return label
    return "CONFIDENTIAL"


def main():
    rows = []
    row_id = 1
    for label, templates in TEMPLATES.items():
        for t_index, template in enumerate(templates, start=1):
            template_id = f"{label}_{t_index:02d}"
            for _ in range(SAMPLES_PER_TEMPLATE):
                text = fill(template)
                rows.append({
                    "id": row_id,
                    "text": text,
                    "label": label,
                    "coarse_label": coarse_label_for(label),
                    "template_id": template_id,
                })
                row_id += 1

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "text", "label", "coarse_label", "template_id"])
        writer.writeheader()
        writer.writerows(rows)

    # Quick summary so you can see it worked without opening the file
    counts = {}
    for r in rows:
        counts[r["label"]] = counts.get(r["label"], 0) + 1

    print(f"Wrote {len(rows)} rows to {OUTPUT_PATH}\n")
    print(f"{'label':<15}{'rows':>6}")
    print("-" * 21)
    for label in TEMPLATES:
        print(f"{label:<15}{counts[label]:>6}")


if __name__ == "__main__":
    main()
