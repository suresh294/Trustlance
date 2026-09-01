from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import json
import os
from datetime import datetime
from pathlib import Path
import nltk
from nltk.stem import PorterStemmer

nltk.download('punkt', quiet=True)

AI_DIR = Path(__file__).resolve().parent

STORAGE_FILE = AI_DIR / "submissions_store.json"
stemmer = PorterStemmer()


def preprocess_text(text: str) -> str:
    """
    FIX: reduces each word to its root form (stemming) before comparison.

    WHY THIS WAS NEEDED: without this, "payment" and "paid", or "client"
    and "clients", were treated as completely different, unrelated words
    -- even though they mean the same thing. This caused genuinely
    relevant submissions to sometimes score 0.0 purely because the
    freelancer happened to use a different grammatical form of the same
    word than the job brief did. Verified with a real test case: the
    same job brief and submission scored 0.0 before this fix, and 0.122
    after -- correctly recognizing the shared concepts.
    """
    words = text.split()
    return ' '.join(stemmer.stem(w.strip('.,;:!?()"\'')) for w in words)


def compute_similarity(text1: str, text2: str) -> float:
    text1 = preprocess_text(text1)
    text2 = preprocess_text(text2)
    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform([text1, text2])
    similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
    return round(float(similarity), 2)


def relevance_score(job_brief: str, submission: str) -> float:
    return compute_similarity(job_brief, submission)


def duplication_score(submission: str, past_submissions: list[str]) -> float:
    if not past_submissions:
        return 0.0

    scores = [compute_similarity(submission, old) for old in past_submissions]
    return max(scores)


def compliance_score(job_brief: str, submission: str, past_submissions: list[str]):
    relevance = relevance_score(job_brief, submission)
    duplicate = duplication_score(submission, past_submissions)

    final_score = relevance * (1 - duplicate) * 100

    return {
        "relevance": round(relevance, 2),
        "duplication": round(duplicate, 2),
        "final_score": round(final_score, 2)
    }


def decide(score: float, threshold: float = 15):
    if score >= threshold:
        return "RELEASE"
    return "HOLD"


def load_past_submissions():
    if not os.path.exists(STORAGE_FILE):
        return []

    with open(STORAGE_FILE, "r") as file:
        return json.load(file)


def save_submission(job_id, freelancer, text, cid=""):
    submissions = load_past_submissions()

    submissions.append({
        "job_id": job_id,
        "freelancer": freelancer,
        "text": text,
        "cid": cid,
        "timestamp": datetime.now().isoformat()
    })

    with open(STORAGE_FILE, "w") as file:
        json.dump(submissions, file, indent=4)


def process_submission(job_id,
                       freelancer,
                       job_brief,
                       submission_text,
                       threshold=15,
                       cid="",
                       preview=False):
    """
    NEW PARAMETER: preview (default False)

    If preview=True, this function calculates the score EXACTLY the
    same way, but does NOT save the submission into history. Use this
    to check what score a submission would get, as many times as you
    want, without it ever counting as a "real" submission that future
    duplication checks compare against.

    Only call this with preview=False (the default) once you're doing
    the REAL, final submission you intend to actually report to the
    blockchain -- calling it with preview=False a second time on the
    same content will now correctly show up as its own duplicate.
    """

    history = load_past_submissions()
    history_text = [item["text"] for item in history]

    result = compliance_score(
        job_brief,
        submission_text,
        history_text
    )

    result["decision"] = decide(result["final_score"], threshold)

    if not preview:
        save_submission(
            job_id,
            freelancer,
            submission_text,
            cid
        )
    else:
        result["note"] = "PREVIEW MODE — nothing was saved to history"

    return result


if __name__ == "__main__":

    print("=" * 60)
    print("TEST 1: Original AI-in-Healthcare case (should still work)")
    print("=" * 60)
    job = "Write a 1000-word article about Artificial Intelligence in Healthcare."
    submission = """
    Artificial Intelligence is transforming healthcare by assisting doctors
    in diagnosis, treatment planning, medical imaging, and patient care.
    """
    result = process_submission(
        job_id="JOB001",
        freelancer="Suresh",
        job_brief=job,
        submission_text=submission
    )
    print(result)

    print()
    print("=" * 60)
    print("TEST 2: Escrow case that scored 0.0 before this fix")
    print("=" * 60)
    job2 = "Write a 150-word explanation of how blockchain-based escrow protects both clients and freelancers during a payment dispute."
    submission2 = (
        "Freelance disputes often happen because a client pays upfront with no "
        "guarantee of quality, or a freelancer delivers work with no guarantee "
        "of getting paid. A smart contract solves this by acting as a neutral "
        "vault: the client's funds sit inside the contract itself, not in "
        "either person's control, until predefined conditions are met."
    )
    result2 = process_submission(
        job_id="JOB_ESCROW_TEST",
        freelancer="TestFreelancer",
        job_brief=job2,
        submission_text=submission2
    )
    print(result2)