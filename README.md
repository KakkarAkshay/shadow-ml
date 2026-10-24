# Shadow-ml

ML-based text classifier for the Shadow AI Security & Data Loss
Prevention Gateway. It detects sensitive data (API keys, passwords,
emails, phone numbers, payment cards and other PII) in text prompts
before they are sent to external AI tools.

## Tech stack
- Python, scikit-learn, pandas
- Models: Naive Bayes, Logistic Regression, Linear SVM (final model chosen after evaluation)

## Project structure
- `ml/classifier.py`: classifier inference code
- `ml/test_classifier.py`: automated tests
- `generate_dataset.py`, `clean_dataset.py`, `split_dataset.py`: dataset pipeline
- `train_and_evaluate.py`, `finalize_model.py`: training and evaluation
- `final_model.joblib`: the trained final model
- `reports/`: evaluation reports and confusion matrices

## Run locally
1. Clone the repo: `git clone https://github.com/KakkarAkshay/shadow-ml.git`
2. Go into the folder: `cd shadow-ml`
3. Create a virtual environment: `python -m venv .venv`
4. Activate it (Git Bash): `source .venv/Scripts/activate`
5. Install dependencies: `pip install -r requirements.txt`
6. Copy `.env.example` to `.env` and adjust values if needed
7. Run the tests: `pytest ml/test_classifier.py`

## Branching
- `main`: stable, deployed
- `develop`: integration branch
- `feature/*`: new work, merged through pull requests
