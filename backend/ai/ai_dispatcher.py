from backend.ai.text_compliance_checker import process_submission
from backend.ai.code_compliance_checker import process_code_submission
from backend.ai.image_compliance_checker import process_image_submission
from backend.ai.audio_compliance_checker import process_audio_submission


def process_ai_submission(submission_type, **kwargs):

    submission_type = submission_type.lower()

    if submission_type == "text":

        return process_submission(
            job_id=kwargs["job_id"],
            freelancer=kwargs["freelancer"],
            job_brief=kwargs["job_brief"],
            submission_text=kwargs["submission_text"],
            threshold=kwargs.get("threshold", 15),
            cid=kwargs.get("cid", ""),
            preview=kwargs.get("preview", True)
        )

    elif submission_type == "code":

        return process_code_submission(
            job_id=kwargs["job_id"],
            freelancer=kwargs["freelancer"],
            code=kwargs["code"],
            function_name=kwargs["function_name"],
            test_cases=kwargs["test_cases"],
            threshold=kwargs.get("threshold", 60),
            cid=kwargs.get("cid", ""),
            preview=kwargs.get("preview", True)
        )

    elif submission_type == "image":

        return process_image_submission(
            job_id=kwargs["job_id"],
            freelancer=kwargs["freelancer"],
            job_description=kwargs["job_description"],
            image_path=kwargs["image_path"],
            threshold=kwargs.get("threshold", 15),
            cid=kwargs.get("cid", ""),
            preview=kwargs.get("preview", True)
            )

    elif submission_type == "audio":

        return process_audio_submission(
    job_id=kwargs["job_id"],
    freelancer=kwargs["freelancer"],
    job_description=kwargs["job_brief"],
    audio_path=kwargs["audio_path"],
    threshold=kwargs["threshold"],
    cid=kwargs.get("cid", "")
)

    else:
        raise ValueError(
            f"Unsupported submission type: {submission_type}"
        )


if __name__ == "__main__":

    result = process_ai_submission(
        submission_type="audio",
        job_id="JOB003",
        freelancer="Suresh",
        job_description="Create a short professional voice advertisement",
        audio_path=r"..\test_audio\sample.mp3",
        threshold=60,
        preview=True
    )
    print(result)