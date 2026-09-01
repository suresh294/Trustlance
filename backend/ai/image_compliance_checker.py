import json
import os
from datetime import datetime
from pathlib import Path

import imagehash
from PIL import Image
from sklearn.metrics.pairwise import cosine_similarity


# ============================================================
# PROJECT PATH
# ============================================================

AI_DIR = Path(__file__).resolve().parent

IMAGE_STORAGE_FILE = (
    AI_DIR / "image_submissions_store.json"
)


# ============================================================
# CLIP GLOBAL VARIABLES
# ============================================================

_clip_model = None
_clip_preprocess = None
_clip_tokenizer = None
_clip_device = None


# ============================================================
# LOAD CLIP MODEL
# ============================================================

def get_clip_model():

    global _clip_model
    global _clip_preprocess
    global _clip_tokenizer
    global _clip_device

    if _clip_model is None:

        import torch
        import open_clip

        _clip_device = (
            "cuda"
            if torch.cuda.is_available()
            else "cpu"
        )

        _clip_model, _, _clip_preprocess = (
            open_clip.create_model_and_transforms(
                "ViT-B-32",
                pretrained="laion2b_s34b_b79k"
            )
        )

        _clip_tokenizer = (
            open_clip.get_tokenizer("ViT-B-32")
        )

        _clip_model.to(_clip_device)

        _clip_model.eval()

    return (
        _clip_model,
        _clip_preprocess,
        _clip_tokenizer,
        _clip_device
    )


# ============================================================
# TEXT ENCODING
# ============================================================

def encode_text(text: str):

    import torch

    model, _, tokenizer, device = get_clip_model()

    tokens = tokenizer([text]).to(device)

    with torch.no_grad():

        features = model.encode_text(tokens)

    features /= features.norm(
        dim=-1,
        keepdim=True
    )

    return features.cpu().numpy()


# ============================================================
# IMAGE ENCODING
# ============================================================

def encode_image(image_path: str):

    import torch

    model, preprocess, _, device = get_clip_model()

    image = (
        Image.open(image_path)
        .convert("RGB")
    )

    image = (
        preprocess(image)
        .unsqueeze(0)
        .to(device)
    )

    with torch.no_grad():

        features = model.encode_image(image)

    features /= features.norm(
        dim=-1,
        keepdim=True
    )

    return features.cpu().numpy()


# ============================================================
# IMAGE RELEVANCE
# ============================================================

def image_relevance_score(
    job_description: str,
    image_path: str
) -> float:

    text_vector = encode_text(
        job_description
    )

    image_vector = encode_image(
        image_path
    )

    score = cosine_similarity(
        text_vector,
        image_vector
    )[0][0]

    return float(score)


# ============================================================
# IMAGE HASH
# ============================================================

def image_hash(image_path: str):

    image = (
        Image.open(image_path)
        .convert("RGB")
    )

    return imagehash.phash(image)


# ============================================================
# IMAGE SIMILARITY
# ============================================================

def image_similarity(
    hash1,
    hash2
) -> float:

    distance = hash1 - hash2

    similarity = (
        1 - (distance / 64)
    )

    return max(0, similarity)


# ============================================================
# DUPLICATION CHECK
# ============================================================

def image_duplication_score(
    image_path: str,
    history: list
) -> float:

    if not history:

        return 0.0

    new_hash = image_hash(
        image_path
    )

    scores = []

    for img in history:

        if os.path.exists(img):

            old_hash = image_hash(img)

            similarity = image_similarity(
                new_hash,
                old_hash
            )

            scores.append(similarity)

    if not scores:

        return 0.0

    return max(scores)


# ============================================================
# COMPLIANCE SCORE
# ============================================================

def compliance_score(
    job_description: str,
    image_path: str,
    history: list
) -> dict:

    relevance = image_relevance_score(
        job_description,
        image_path
    )

    duplicate = image_duplication_score(
        image_path,
        history
    )

    # Only penalize highly similar images
    # Only penalize extremely similar images

    if duplicate >= 0.90:

        duplication_penalty = (
            (duplicate - 0.90) / 0.10
        )

        duplication_penalty = min(
            duplication_penalty,
            1.0
        )

    else:

        duplication_penalty = 0.0


    final_score = (
        relevance
        * (1 - duplication_penalty)
        * 100
    )


    return {

        "relevance": round(
            relevance,
            3
        ),

        "duplication": round(
            duplicate,
            3
        ),

        "final_score": round(
            final_score,
            2
        )

    }

# ============================================================
# DECISION
# ============================================================

def decide(
    score: float,
    threshold: float = 15
) -> str:

    return (
        "RELEASE"
        if score >= threshold
        else "HOLD"
    )


# ============================================================
# LOAD IMAGE HISTORY
# ============================================================

def load_past_images() -> list:

    if not os.path.exists(
        IMAGE_STORAGE_FILE
    ):

        return []

    try:

        with open(
            IMAGE_STORAGE_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if not isinstance(
            data,
            list
        ):

            return []

        return data

    except (
        json.JSONDecodeError,
        OSError
    ):

        return []


# ============================================================
# SAVE IMAGE SUBMISSION
# ============================================================

def save_image_submission(
    job_id: str,
    freelancer: str,
    image_path: str,
    cid: str = ""
) -> None:

    history = load_past_images()

    history.append({

        "job_id": str(job_id),

        "freelancer": str(freelancer),

        "image_path": str(image_path),

        "cid": str(cid),

        "timestamp": datetime.now().isoformat()

    })

    with open(
        IMAGE_STORAGE_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            history,
            file,
            indent=4
        )


# ============================================================
# PROCESS IMAGE SUBMISSION
# ============================================================

def process_image_submission(
    job_id: str,
    freelancer: str,
    job_description: str,
    image_path: str,
    threshold: float = 15,
    cid: str = "",
    preview: bool = True
) -> dict:

    history = load_past_images()

    history_paths = [

        item.get("image_path")

        for item in history

        if item.get("image_path")

    ]

    result = compliance_score(

        job_description,

        image_path,

        history_paths

    )

    result["decision"] = decide(

        result["final_score"],

        threshold

    )

    result["preview"] = preview


    # Save only after a real submission,
    # not during preview/testing.

    if not preview:

        save_image_submission(

            job_id,

            freelancer,

            image_path,

            cid

        )


    return result


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print(
        process_image_submission(

            job_id="TEST_IMAGE",

            freelancer="TEST_FREELANCER",

            job_description=(
                "Create a professional healthy eating "
                "awareness poster with fruits and vegetables"
            ),

            image_path=r"..\test_images\poster.png",

            threshold=15,

            preview=True

        )
    )