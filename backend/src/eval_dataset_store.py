from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List, Dict, Any

from utils.supabase_client import supabase_client
from utils.config_loader import ConfigLoader
from utils.base_models import TestQuestion


config = ConfigLoader()
project_root = Path(__file__).parent.parent
TEST_QUESTIONS_FILE_PATH = (project_root / "evaluation" / "eval_data.jsonl").resolve()


def _owner_id() -> str:
    return config.get_owner_id()


def _row_to_test_question(row: Dict[str, Any]) -> TestQuestion:
    keywords = row.get("keywords") or []
    # Ensure keywords is always a list of strings
    if isinstance(keywords, str):
        keywords = [k.strip() for k in keywords.split(",") if k.strip()]
    elif isinstance(keywords, Iterable):
        keywords = [str(k).strip() for k in keywords if str(k).strip()]
    else:
        keywords = []

    category = row.get("category") or "general"

    return TestQuestion(
        question=row.get("question", ""),
        ground_truth=row.get("ground_truth", ""),
        category=category,
        keywords=keywords,
    )


def _test_question_to_row(tq: TestQuestion) -> Dict[str, Any]:
    return {
        "owner_id": _owner_id(),
        "question": tq.question,
        "ground_truth": tq.ground_truth,
        "category": tq.category,
        "keywords": list(tq.keywords or []),
    }


def load_eval_rows_from_supabase() -> List[TestQuestion]:
    """
    Load eval dataset from Supabase for the current owner_id.
    Returns an empty list if the table is missing or unreachable.
    """
    try:
        resp = (
            supabase_client.table("eval_dataset")
            .select("id, owner_id, question, ground_truth, category, keywords")
            .eq("owner_id", _owner_id())
            .execute()
        )
        rows = resp.data or []
    except Exception:
        return []

    return [_row_to_test_question(row) for row in rows]


def save_eval_rows_to_supabase(rows: List[TestQuestion], replace: bool = True) -> None:
    """
    Persist eval dataset to Supabase.
    If replace=True, existing rows for this owner_id are cleared first.
    """
    try:
        if replace:
            supabase_client.table("eval_dataset").delete().eq("owner_id", _owner_id()).execute()

        if not rows:
            return

        payload = [_test_question_to_row(tq) for tq in rows]
        supabase_client.table("eval_dataset").upsert(payload).execute()
    except Exception:
        # Non-fatal: evaluation can still fall back to JSONL
        return


def clear_eval_rows() -> None:
    """Delete all eval dataset rows for the current owner_id."""
    try:
        supabase_client.table("eval_dataset").delete().eq("owner_id", _owner_id()).execute()
    except Exception:
        return


def _load_from_jsonl() -> List[TestQuestion]:
    tests: List[TestQuestion] = []
    if not TEST_QUESTIONS_FILE_PATH.exists():
        return tests
    with open(TEST_QUESTIONS_FILE_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            tests.append(TestQuestion(**data))
    return tests


def ensure_seed_from_jsonl_if_empty() -> List[TestQuestion]:
    """
    Ensure Supabase has rows for this owner_id; if empty and JSONL exists,
    seed from JSONL and return those tests.
    """
    existing = load_eval_rows_from_supabase()
    if existing:
        return existing

    tests = _load_from_jsonl()
    if tests:
        save_eval_rows_to_supabase(tests, replace=True)
    return tests

