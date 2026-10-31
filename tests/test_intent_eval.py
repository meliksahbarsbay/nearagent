"""Compares real parser output with expected JSON. Run with: pytest -m live"""
import asyncio
import json
from pathlib import Path

import pytest
from dotenv import load_dotenv

from app.intent import parse_intent, providers

load_dotenv()

CASES = json.loads((Path(__file__).parent / "intent_cases.json").read_text(encoding="utf-8"))


def test_case_counts():
    languages = [case["expected"]["language"] for case in CASES]
    assert languages.count("tr") == 15
    assert languages.count("en") == 15


@pytest.mark.live
@pytest.mark.parametrize("case", CASES, ids=[case["text"] for case in CASES])
def test_parser_matches_expected(case):
    if not providers():
        pytest.skip("no provider key configured")
    assert asyncio.run(parse_intent(case["text"])).model_dump() == case["expected"]
