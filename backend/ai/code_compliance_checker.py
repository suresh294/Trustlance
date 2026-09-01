import ast
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path


# ============================================================
# STORAGE
# ============================================================

AI_DIR = Path(__file__).resolve().parent
CODE_STORAGE_FILE = AI_DIR / "code_submissions_store.json"


# ============================================================
# PART 1: CORRECTNESS CHECK
# ============================================================

def run_test_case(
    code: str,
    function_name: str,
    test_input,
    timeout_seconds: int = 5
):
    runner_script = f"""
{code}

import json

test_input = {test_input!r}

if isinstance(test_input, (list, tuple)):
    result = {function_name}(*test_input)
else:
    result = {function_name}(test_input)

print(json.dumps(result))
"""

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".py",
        delete=False,
        encoding="utf-8"
    ) as f:
        f.write(runner_script)
        temp_path = f.name

    try:
        completed = subprocess.run(
            [sys.executable, temp_path],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )

        if completed.returncode != 0:
            return {
                "success": False,
                "error": completed.stderr.strip()[-300:]
            }

        output = json.loads(
            completed.stdout.strip().splitlines()[-1]
        )

        return {
            "success": True,
            "output": output
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Timed out (possible infinite loop)"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def correctness_score(
    code: str,
    function_name: str,
    test_cases: list[tuple]
) -> float:

    if not test_cases:
        return 0.0

    passed = 0

    for test_input, expected_output in test_cases:

        result = run_test_case(
            code,
            function_name,
            test_input
        )

        if (
            result["success"]
            and result["output"] == expected_output
        ):
            passed += 1

    return passed / len(test_cases)


# ============================================================
# PART 2: AST DUPLICATION CHECK
# ============================================================

def get_normalized_ast(code: str) -> str:
    """
    Converts Python code into a normalized AST representation.

    Variable/function argument names are normalized so that:
        def add_numbers(a, b)
    and
        def add_numbers(x, y)

    can still be recognized as structurally similar.

    Comments and formatting do not affect the comparison.
    """

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return ""

    class NormalizeAST(ast.NodeTransformer):

        def visit_Name(self, node):
            node.id = "VAR"
            return node

        def visit_arg(self, node):
            node.arg = "ARG"
            return node

        def visit_Constant(self, node):
            # Keep the TYPE of constant but hide its actual value.
            if isinstance(node.value, bool):
                node.value = "BOOL"
            elif isinstance(node.value, (int, float)):
                node.value = "NUMBER"
            elif isinstance(node.value, str):
                node.value = "STRING"
            elif node.value is None:
                node.value = "NONE"

            return node

        def visit_FunctionDef(self, node):
            # Normalize function name too.
            node.name = "FUNCTION"
            return self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node):
            node.name = "FUNCTION"
            return self.generic_visit(node)

    tree = NormalizeAST().visit(tree)

    ast.fix_missing_locations(tree)

    return ast.dump(
        tree,
        annotate_fields=True,
        include_attributes=False
    )


def code_similarity(
    code_a: str,
    code_b: str
) -> float:
    """
    Calculates structural similarity between two Python programs.

    Unlike the old implementation, this compares the actual normalized
    AST structure instead of simply counting AST node types.

    This reduces false duplication scores between unrelated programs.
    """

    normalized_a = get_normalized_ast(code_a)
    normalized_b = get_normalized_ast(code_b)

    if not normalized_a or not normalized_b:
        return 0.0

    if normalized_a == normalized_b:
        return 1.0

    from difflib import SequenceMatcher

    similarity = SequenceMatcher(
        None,
        normalized_a,
        normalized_b
    ).ratio()

    return round(similarity, 3)


def code_duplication_score(
    new_code: str,
    past_code_submissions: list[str]
) -> float:
    """
    Finds the highest structural similarity between the new submission
    and previous submissions.

    0.0 = no meaningful similarity
    1.0 = identical normalized structure
    """

    if not past_code_submissions:
        return 0.0

    scores = []

    for past_code in past_code_submissions:
        score = code_similarity(
            new_code,
            past_code
        )

        scores.append(score)

    return max(scores) if scores else 0.0
# ============================================================
# PART 3: STORAGE
# ============================================================

def load_past_code_submissions() -> list[dict]:

    if not CODE_STORAGE_FILE.exists():
        return []

    try:
        with open(
            CODE_STORAGE_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            return json.load(f)

    except (json.JSONDecodeError, OSError):
        return []


def save_code_submission(
    job_id: str,
    freelancer: str,
    code: str,
    cid: str = ""
) -> None:

    submissions = load_past_code_submissions()

    submissions.append({
        "job_id": str(job_id),
        "freelancer": freelancer,
        "code": code,
        "cid": cid,
        "timestamp": datetime.now().isoformat(),
    })

    with open(
        CODE_STORAGE_FILE,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            submissions,
            f,
            indent=2
        )


# ============================================================
# PART 4: CODE SUBMISSION PROCESSOR
# ============================================================

def process_code_submission(
    job_id: str,
    freelancer: str,
    code: str,
    function_name: str,
    test_cases: list[tuple],
    threshold: float = 60.0,
    cid: str = "",
    preview: bool = True
) -> dict:

    past = load_past_code_submissions()

    past_codes = [
        submission["code"]
        for submission in past
    ]

    # Correctness
    correctness = correctness_score(
        code,
        function_name,
        test_cases
    )

    # Duplication
    duplication = code_duplication_score(
        code,
        past_codes
    )

    # Final score
    raw_score = (
        correctness * 100
    ) - (
        duplication * 100
    )

    final_score = max(
        0,
        min(100, raw_score)
    )

    decision = (
        "RELEASE"
        if final_score >= threshold
        else "HOLD"
    )

    # IMPORTANT:
    # Preview mode does NOT modify history.
    if not preview:
        save_code_submission(
            job_id,
            freelancer,
            code,
            cid=cid
        )

    return {
        "relevance": round(correctness, 3),
        "duplication": round(duplication, 3),
        "final_score": round(final_score, 1),
        "decision": decision,
        "preview": preview
    }


# ============================================================
# DEMO / TEST
# ============================================================

if __name__ == "__main__":

    test_cases = [
        ([3, 1, 2], [1, 2, 3]),
        ([5, 4, 3, 2, 1], [1, 2, 3, 4, 5]),
        ([], []),
    ]

    print("=" * 60)
    print("CODE COMPLIANCE CHECKER")
    print("=" * 60)

    # --------------------------------------------------------
    # CASE 1
    # --------------------------------------------------------

    correct_code = """
def sort_numbers(nums):
    return sorted(nums)
"""

    result = process_code_submission(
        "demo-1",
        "demo-freelancer",
        correct_code,
        "sort_numbers",
        test_cases,
        threshold=60,
        preview=True
    )

    print("\nCASE 1: Correct solution")
    print(result)

    # --------------------------------------------------------
    # CASE 2
    # --------------------------------------------------------

    buggy_code = """
def sort_numbers(nums):
    return list(reversed(nums))
"""

    result = process_code_submission(
        "demo-2",
        "demo-freelancer",
        buggy_code,
        "sort_numbers",
        test_cases,
        threshold=60,
        preview=True
    )

    print("\nCASE 2: Incorrect solution")
    print(result)

    # --------------------------------------------------------
    # CASE 3
    # --------------------------------------------------------

    renamed_code = """
def sort_numbers(data):
    return sorted(data)
"""

    # First preview the original code so nothing is saved.
    original_preview = process_code_submission(
        "demo-3",
        "demo-freelancer",
        renamed_code,
        "sort_numbers",
        test_cases,
        threshold=60,
        preview=True
    )

    print("\nCASE 3: Duplicate check preview")
    print(original_preview)

    print("\nHistory file:")
    print(CODE_STORAGE_FILE)

    print("\nNOTE: Demo runs use preview=True.")
    print("No test submission is saved to history.")