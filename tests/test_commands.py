"""Fixed agent commands. These never reach the language model or the network."""
import httpx
import pytest

import app.main as main
from app.agent_api import AgentApiError, agent_ready, read_agent_policy
from app.commands import detect_command
from app.messages import say_budget, say_policy
from tests.test_quote import make_client

SETTINGS = ("NEAR_INTENTS_AGENT_API_KEY", "AGENT_API_KEY", "AGENT_ID", "GRANT_TOKEN")
POLICY = {
    "status": "APPLIED",
    "provider_policy_synced": True,
    "policy": {
        "frozen": False,
        "actions": ["swap", "withdraw"],
        "assets": ["a", "b", "c", "d", "e"],
        "budget": {"daily_usd": "10", "weekly_usd": None, "monthly_usd": None},
    },
    "usage": {
        "budget": {
            "daily": {
                "limit_usd": "10",
                "spent_usd": "2.500000",
                "remaining_usd": "7.500000",
                "resets_at": "2026-11-02T00:00:00Z",
            }
        }
    },
}


@pytest.fixture
def no_agent(monkeypatch):
    for name in SETTINGS:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def agent(monkeypatch):
    monkeypatch.setenv("NEAR_INTENTS_AGENT_API_KEY", "naa_test")
    monkeypatch.setenv("AGENT_ID", "agent-1")


@pytest.fixture
def no_parser(monkeypatch):
    async def fail(text):
        raise AssertionError("commands must not reach the parser")

    monkeypatch.setattr(main, "parse_intent", fail)


def use_policy(monkeypatch, data=POLICY):
    async def read():
        return data

    monkeypatch.setattr(main, "read_agent_policy", read)


def ask(client, text):
    return client.post("/api/ask", json={"text": text}).json()


@pytest.mark.parametrize(
    "text, expected",
    [
        ("politikamı oku", ("policy", "tr")),
        ("Politikamı oku.", ("policy", "tr")),
        ("politikam ne", ("policy", "tr")),
        ("POLİTİKAMI OKU", ("policy", "tr")),
        ("read my policy", ("policy", "en")),
        ("what is my policy", ("policy", "en")),
        ("bütçem ne kadar kaldı", ("budget", "tr")),
        ("bütçem ne kadar", ("budget", "tr")),
        ("butcem ne kadar kaldi", ("budget", "tr")),
        ("how much budget is left", ("budget", "en")),
        ("budget left", ("budget", "en")),
        ("ajanı dondur", ("freeze", "tr")),
        ("Ajanı dondur!", ("freeze", "tr")),
        ("ajanı hemen dondur", ("freeze", "tr")),
        ("freeze the agent", ("freeze", "en")),
        ("emergency stop", ("freeze", "en")),
        ("ajanı acil durdur", ("freeze", "tr")),
        ("acil durdur", ("freeze", "tr")),
        ("ajanı çöz", ("unfreeze", "tr")),
        ("Ajanı çöz.", ("unfreeze", "tr")),
        ("ajanı aç", ("unfreeze", "tr")),
        ("dondurmayı kaldır", ("unfreeze", "tr")),
        ("ajanın dondurmasını kaldır", ("unfreeze", "tr")),
        ("unfreeze the agent", ("unfreeze", "en")),
    ],
)
def test_commands_are_recognized(text, expected):
    assert detect_command(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "2 NEAR'ı USDC'ye çevir",
        "1 SOL kaç dolar",
        "swap 2 NEAR to USDC on Base",
        "merhaba",
        "dondurma fiyatı ne",
        "help",
    ],
)
def test_ordinary_sentences_are_not_commands(text):
    assert detect_command(text) is None


@pytest.mark.parametrize(
    "text", ["politikamı oku", "bütçem ne kadar kaldı", "ajanı dondur", "ajanı çöz"]
)
def test_no_agent_is_said_plainly(no_agent, no_parser, text):
    client, sent = make_client()
    data = ask(client, text)
    assert data["spoken"].startswith("Ajan cüzdanı kurulmadı")
    assert data["language"] == "tr"
    assert sent == []


def test_no_agent_in_english(no_agent, no_parser):
    client, _ = make_client()
    assert ask(client, "read my policy")["spoken"].startswith("The agent wallet is not set up.")


def test_commands_work_with_live_mode_requested_and_no_key(no_agent, no_parser):
    client, _ = make_client()
    data = client.post("/api/ask", json={"text": "politikamı oku", "live": True}).json()
    assert data["spoken"].startswith("Ajan cüzdanı kurulmadı")


def test_policy_is_read_aloud(agent, no_parser, monkeypatch):
    use_policy(monkeypatch)
    client, _ = make_client()
    assert ask(client, "politikamı oku")["spoken"] == (
        "Politika: izinli işlemler takas ve çekim. 5 varlık izinli. "
        "Günlük bütçe 10 dolar. Ajan çalışır durumda."
    )


def test_policy_in_english(agent, no_parser, monkeypatch):
    use_policy(monkeypatch)
    client, _ = make_client()
    assert ask(client, "read my policy")["spoken"] == (
        "Policy: allowed actions are swap and withdraw. 5 assets are allowed. "
        "The daily budget is 10 dollars. The agent is active."
    )


def test_policy_says_when_frozen():
    frozen = {**POLICY, "policy": {**POLICY["policy"], "frozen": True}}
    assert say_policy(frozen, "tr").endswith("Ajan şu an dondurulmuş.")


def test_all_assets_are_spoken_without_a_count():
    open_policy = {**POLICY, "policy": {**POLICY["policy"], "assets": "any"}}
    assert "Tüm varlık izinli." in say_policy(open_policy, "tr")


@pytest.mark.parametrize(
    "changes",
    [{"status": "SIGNED"}, {"provider_policy_synced": False}, {"policy": None}],
)
def test_policy_not_in_force_is_never_read_as_rules(changes):
    assert say_policy({**POLICY, **changes}, "tr").startswith("Politika henüz yürürlükte değil.")


def test_ids_stay_out_of_the_spoken_policy():
    assert "a" not in say_policy(POLICY, "en").split()


def test_budget_is_read_aloud(agent, no_parser, monkeypatch):
    use_policy(monkeypatch)
    client, _ = make_client()
    assert ask(client, "bütçem ne kadar kaldı")["spoken"] == (
        "Günlük bütçenden 7,5 dolar kaldı. Sınır 10 dolar."
    )


def test_remaining_budget_rounds_down():
    data = {
        "usage": {
            "budget": {"daily": {"limit_usd": "10", "remaining_usd": "1.999999"}},
        }
    }
    assert say_budget(data, "en").startswith("You have 1.99 dollars left")


def test_no_daily_cap():
    data = {"usage": {"budget": {"daily": {"limit_usd": None}}}}
    assert say_budget(data, "tr").startswith("Günlük bütçe sınırı yok.")


def test_read_failure_is_spoken_without_a_code(agent, no_parser, monkeypatch):
    async def fail():
        raise AgentApiError(503, "provider_unavailable")

    monkeypatch.setattr(main, "read_agent_policy", fail)
    client, _ = make_client()
    data = ask(client, "politikamı oku")
    assert data["spoken"] == "Ajan bilgisi alınamadı. Biraz sonra yeniden dene."
    assert "provider" not in data["spoken"]


def test_key_alone_is_not_an_agent(no_agent, monkeypatch):
    monkeypatch.setenv("NEAR_INTENTS_AGENT_API_KEY", "naa_test")
    assert agent_ready() is False


def test_reading_sends_no_grant_token(agent, monkeypatch):
    monkeypatch.setenv("GRANT_TOKEN", "ngt_test")
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json=POLICY)

    import asyncio

    asyncio.run(read_agent_policy(httpx.MockTransport(handler)))
    assert seen[0].url.path == "/v1/agents/agent-1/policy"
    assert "X-Grant-Token" not in seen[0].headers
