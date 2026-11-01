"""Compares real parser output with expected JSON. Run with: pytest -m live"""
import asyncio
import json
from pathlib import Path

import pytest
from dotenv import load_dotenv

from app.intent import parse_intent, providers

load_dotenv()

HERE = Path(__file__).parent
CASES = json.loads((HERE / "intent_cases.json").read_text(encoding="utf-8"))
AMOUNT_CASES = json.loads((HERE / "amount_cases.json").read_text(encoding="utf-8"))


def test_case_counts():
    languages = [case["expected"]["language"] for case in CASES]
    assert languages.count("tr") == 15
    assert languages.count("en") == 15


def check(case):
    if not providers():
        pytest.skip("no provider key configured")
    found = asyncio.run(parse_intent(case["text"])).model_dump()
    assert {key: found[key] for key in case["expected"]} == case["expected"]


@pytest.mark.live
@pytest.mark.parametrize("case", CASES, ids=[case["text"] for case in CASES])
def test_parser_matches_expected(case):
    check(case)


@pytest.mark.live
@pytest.mark.parametrize("case", AMOUNT_CASES, ids=[case["text"] for case in AMOUNT_CASES])
def test_amounts_match_expected(case):
    check(case)
