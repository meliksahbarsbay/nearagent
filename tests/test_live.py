"""Live mode rules. These run without keys and make no Agent API call."""
import pytest

import app.main as main
from tests.test_quote import make_client, payload, use_intent

LIVE_ENV = ("NEAR_INTENTS_AGENT_API_KEY", "AGENT_API_KEY", "AGENT_ID", "GRANT_TOKEN")


@pytest.fixture
def no_live(monkeypatch):
    for name in LIVE_ENV:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def live(monkeypatch):
    monkeypatch.setenv("NEAR_INTENTS_AGENT_API_KEY", "naa_test")
    monkeypatch.setenv("AGENT_ID", "agent")
    monkeypatch.setenv("GRANT_TOKEN", "ngt_test")


def offer(client, **changes):
    return client.post("/api/quote", json=payload(live=True, **changes)).json()


def answer(client, key, text):
    return client.post("/api/ask", json={"text": text, "pending": key}).json()


def test_mode_stays_off_without_a_key(no_live):
    client, _ = make_client()
    response = client.post("/api/mode", json={"live": True, "lang": "tr"})
    assert response.status_code == 409
    assert response.json()["spoken"].startswith("Canlı mod için ajan cüzdanı kurulmadı.")


@pytest.mark.parametrize("missing", ["NEAR_INTENTS_AGENT_API_KEY", "AGENT_ID", "GRANT_TOKEN"])
def test_every_setting_is_needed(live, monkeypatch, missing):
    monkeypatch.delenv(missing)
    client, _ = make_client()
    assert client.post("/api/mode", json={"live": True}).status_code == 409


def test_short_key_name_also_counts(live, monkeypatch):
    monkeypatch.delenv("NEAR_INTENTS_AGENT_API_KEY")
    monkeypatch.setenv("AGENT_API_KEY", "naa_test")
    client, _ = make_client()
    assert client.post("/api/mode", json={"live": True}).json()["live"] is True


def test_quote_refuses_live_without_a_key(no_live):
    client, sent = make_client()
    data = offer(client)
    assert data["error"] == "live_not_configured"
    assert "pending" not in data
    assert sent == []


def test_ask_refuses_live_without_a_key(no_live, monkeypatch):
    client, sent = make_client()
    use_intent(monkeypatch, action="swap", amount="1", from_token="USDC", to_token="SOL")
    data = client.post("/api/ask", json={"text": "x", "live": True}).json()
    assert data["error"] == "live_not_configured"
    assert sent == []


def test_turning_live_off_needs_no_key(no_live):
    client, _ = make_client()
    data = client.post("/api/mode", json={"live": False}).json()
    assert data["live"] is False


def test_live_quote_is_labelled_and_asks_for_a_typed_word(live):
    client, _ = make_client()
    data = offer(client)
    assert data["mode"] == "live"
    assert data["confirm_button"] is True
    assert data["spoken"].startswith("Canlı mod. Veriyorsun:")
    assert data["spoken"].endswith("Onaylıyor musun? Evet yaz ya da Onayla düğmesine bas.")
    assert "Enter" not in data["spoken"]


def test_live_still_requests_only_dry_quotes(live):
    client, sent = make_client()
    offer(client)
    assert sent[0]["dry"] is True


def test_empty_enter_never_confirms_in_live_mode(live):
    client, _ = make_client()
    key = offer(client)["pending"]
    for _ in range(3):
        data = answer(client, key, "")
        assert data["spoken"].startswith("Canlı modda Enter onay sayılmaz.")
        assert data["pending"] == key
        assert data["confirm_button"] is True
    assert answer(client, key, "evet")["action"] == "confirmed"


@pytest.mark.parametrize("blank", ["", "   ", "\n"])
def test_whitespace_is_an_empty_enter(live, blank):
    client, _ = make_client()
    key = offer(client)["pending"]
    assert answer(client, key, blank)["action"] == "confirm"


def test_empty_enter_cannot_pass_the_large_amount_question(live):
    client, _ = make_client(amountInUsd="500.00", amountOutUsd="498.76")
    first = offer(client)
    assert first["spoken"].endswith(
        "Yaklaşık beş yüz dolar mı dedin? Evet yaz ya da Onayla düğmesine bas. "
        "Değilse hayır yaz ya da Esc'e bas."
    )
    key = first["pending"]
    assert answer(client, key, "")["action"] == "large"

    second = answer(client, key, "evet")
    assert second["spoken"] == "Onaylıyor musun? Evet yaz ya da Onayla düğmesine bas."
    assert answer(client, key, "")["action"] == "confirm"
    assert answer(client, key, "evet")["action"] == "confirmed"


@pytest.mark.parametrize("word", ["evet", "EVET", "yes", "Yes."])
def test_typed_word_confirms_but_moves_nothing(live, word):
    client, sent = make_client()
    key = offer(client)["pending"]
    data = answer(client, key, word)
    assert data["mode"] == "live"
    assert data["spoken"].startswith("Canlı işlem henüz bağlı değil, para hareket etmedi.")
    assert "pending" not in data
    assert len(sent) == 1


def test_amount_answer_stays_in_live_mode(live, monkeypatch):
    client, _ = make_client()
    use_intent(monkeypatch, action="swap", from_token="USDC", to_token="SOL")
    key = client.post("/api/ask", json={"text": "x", "live": True}).json()["pending"]
    data = answer(client, key, "10")
    assert data["mode"] == "live"
    assert answer(client, data["pending"], "")["action"] == "confirm"


def test_cancel_works_in_live_mode(live):
    client, _ = make_client()
    key = offer(client)["pending"]
    assert answer(client, key, "iptal")["action"] == "cancelled"


def test_dry_mode_keeps_empty_enter(live):
    client, _ = make_client()
    key = client.post("/api/quote", json=payload()).json()["pending"]
    assert answer(client, key, "")["spoken"] == "Deneme modu: işlem yapılmadı."


def test_dry_quote_shows_no_confirm_button(no_live):
    client, _ = make_client()
    assert client.post("/api/quote", json=payload()).json()["confirm_button"] is False


def test_main_has_no_way_to_reach_the_agent_client():
    assert not hasattr(main, "AgentApi")
    assert not hasattr(main, "create_grant_credential")
