import json
import os
from datetime import datetime

import librosa
import numpy as np
from pathlib import Path

AI_DIR = Path(__file__).resolve().parent

AUDIO_STORAGE_FILE = AI_DIR / "audio_submissions_store.json"

_whisper_model = None


def get_whisper_model():
    global _whisper_model

    if _whisper_model is None:
        import whisper

        _whisper_model = whisper.load_model("base")

    return _whisper_model


def transcribe(audio_path):
    """Convert submitted audio into text using Whisper."""
    model = get_whisper_model()

    result = model.transcribe(
        str(audio_path),
        fp16=False,
    )

    return result.get("text", "").strip()


def mfcc_features(audio_path):
    """Extract audio features."""
    y, sr = librosa.load(
        str(audio_path),
        sr=None,
    )

    mfccs = librosa.feature.mfcc(
        y=y,
        sr=sr,
        n_mfcc=20,
    )[1:]

    mean = np.mean(mfccs, axis=1)
    std = np.std(mfccs, axis=1)

    return np.concatenate([mean, std])


def duplication_score(new_transcript, history):
    """Compare transcript with previous audio submissions."""
    if not history:
        return 0.0

    from backend.ai.text_compliance_checker import compute_similarity

    scores = []

    for record in history:
        old_transcript = record.get("transcript", "")

        if old_transcript:
            similarity = compute_similarity(
                new_transcript,
                old_transcript,
            )

            scores.append(float(similarity))

    return max(scores) if scores else 0.0


def decide(score, threshold):
    """Same decision rule as the blockchain."""
    return (
        "RELEASE"
        if float(score) >= float(threshold)
        else "HOLD"
    )


def load_history():
    """Load previous audio submissions safely."""
    if not os.path.exists(AUDIO_STORAGE_FILE):
        return []

    try:
        with open(
            AUDIO_STORAGE_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        return data if isinstance(data, list) else []

    except (json.JSONDecodeError, OSError):
        print(
            "Warning: Invalid audio history file. "
            "Starting with empty history."
        )

        return []


def save_submission(
    job_id,
    freelancer,
    audio_path,
    transcript,
    cid="",
):
    """Save submission permanently for duplication checking."""
    history = load_history()

    history.append(
        {
            "job_id": int(job_id),
            "freelancer": str(freelancer),
            "audio_path": str(audio_path),
            "transcript": str(transcript),
            "cid": str(cid),
            "timestamp": datetime.now().isoformat(),
        }
    )

    with open(
        AUDIO_STORAGE_FILE,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            history,
            file,
            indent=4,
            ensure_ascii=False,
        )


def process_audio_submission(
    job_id,
    freelancer,
    job_description,
    audio_path,
    threshold=60,
    cid="",
):
    """Run the TrustLance audio compliance checker."""
    from backend.ai.text_compliance_checker import compute_similarity

    print("Transcribing audio...")

    history = load_history()
    new_transcript = transcribe(audio_path)

    print("Calculating relevance...")

    relevance = float(
        compute_similarity(
            str(job_description),
            new_transcript,
        )
    )

    print("Checking duplication...")

    duplicate = float(
        duplication_score(
            new_transcript,
            history,
        )
    )

    final_score = relevance * (1 - duplicate) * 100

    final_score = round(
        max(
            0.0,
            min(100.0, final_score),
        ),
        2,
    )

    decision = decide(
        final_score,
        threshold,
    )

    result = {
        "relevance": round(relevance, 3),
        "duplication": round(duplicate, 3),
        "final_score": final_score,
        "threshold": float(threshold),
        "decision": decision,
    }

    save_submission(
        job_id=job_id,
        freelancer=freelancer,
        audio_path=audio_path,
        transcript=new_transcript,
        cid=cid,
    )

    return result


if __name__ == "__main__":
    print("=" * 60)
    print("TRUSTLANCE AUDIO AI COMPLIANCE CHECKER")
    print("=" * 60)
    print("Audio checker loaded successfully.")