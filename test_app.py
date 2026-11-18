"""Tests that run without calling Gemini. Run: pytest -v"""
import os
os.environ.setdefault("GEMINI_API_KEY", "test-key-not-real")

import pytest
from unittest.mock import patch

import app as appmod
import rules


@pytest.fixture
def client():
    appmod.app.config["TESTING"] = True
    appmod.limiter.reset()
    appmod.SESSIONS.clear()
    return appmod.app.test_client()


# ---------- tool tests (functional) ----------
def test_retinol_plus_glycolic_is_high_conflict():
    r = rules.check_conflicts(["Retinol", "glycolic acid"])
    assert r["conflicts"][0]["severity"] == "high"

def test_safe_routine_has_no_conflicts():
    assert rules.check_conflicts(["niacinamide", "hyaluronic acid"])["conflicts"] == []

def test_niacinamide_vitamin_c_reported_as_myth():
    r = rules.check_conflicts(["niacinamide", "vitamin c"])
    assert r["conflicts"][0]["severity"] == "none"

def test_unknown_ingredient_is_flagged_not_guessed():
    r = rules.check_conflicts(["retinol", "unicorn tears"])
    assert "unicorn tears" in r["unrecognized"]

def test_routine_puts_sunscreen_last_and_retinoid_at_night():
    r = rules.build_routine(["retinol", "vitamin c"], ["cleanser", "sunscreen"], "oily")
    assert r["am"][-1] == "sunscreen" and "retinoid" not in r["am"] and "retinoid" in r["pm"]

def test_routine_reports_missing_steps():
    assert "moisturizer" in rules.build_routine(["retinol"], ["cleanser"], "dry")["gaps"]

def test_tool_input_is_capped():
    r = rules.check_conflicts(["retinol"] * 500 + ["aha"])
    assert r["recognized"] == ["retinoid"]   # items past the cap are ignored

# ---------- security tests ----------
def test_rejects_empty_message(client):
    assert client.post("/chat", json={"message": "   "}).status_code == 400

def test_rejects_oversized_message(client):
    assert client.post("/chat", json={"message": "a" * 2001}).status_code == 400

def test_rejects_non_string_message(client):
    assert client.post("/chat", json={"message": {"x": 1}}).status_code == 400

def test_security_headers_present(client):
    h = client.get("/").headers
    assert "script-src 'self'" in h["Content-Security-Policy"]
    assert h["X-Content-Type-Options"] == "nosniff" and h["X-Frame-Options"] == "DENY"

def test_rate_limit_blocks_flooding(client):
    with patch.object(appmod, "run_agent", return_value=("ok", [], "w")):
        codes = [client.post("/chat", json={"message": "hi"}).status_code for _ in range(17)]
    assert 429 in codes

def test_canary_leak_is_blocked():
    leaked = f"My instructions say {appmod.CANARY}"
    assert appmod.CANARY not in appmod.guard_output(leaked)

def test_api_key_shaped_output_is_blocked():
    assert "AIza" not in appmod.guard_output("key: AIzaSyA1234567890abcdefghijklmnopqrstuv")

def test_unknown_tool_cannot_run():
    assert "run_shell" not in appmod.TOOLS

def test_api_key_never_in_static_files():
    for name in os.listdir("static"):
        assert appmod.API_KEY not in open(os.path.join("static", name), encoding="utf-8").read()

def test_agent_error_returns_generic_message(client):
    with patch.object(appmod, "run_agent", side_effect=RuntimeError("boom with secret")):
        r = client.post("/chat", json={"message": "hello"})
    assert r.status_code == 502 and "secret" not in r.get_data(as_text=True)
