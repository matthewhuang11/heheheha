import pytest
from scoutbot.talk.triage import categorize, parse_facts
from scoutbot.types import TriageFacts

def cat(**kw): return categorize(TriageFacts(**kw), "test").category

def test_triage_rules_in_order():
    assert cat(can_walk="yes", trapped="yes") == "MINOR"           # walking wounded first (START)
    assert cat(responsive="no") == "IMMEDIATE"
    assert cat(responsive="yes", breathing_trouble="yes") == "IMMEDIATE"
    assert cat(responsive="yes", visible_bleeding="yes") == "IMMEDIATE"
    assert cat(responsive="yes", trapped="yes") == "IMMEDIATE"
    assert cat(responsive="yes", can_walk="no") == "DELAYED"
    assert cat() == "UNKNOWN"

def test_always_preliminary():
    assert categorize(TriageFacts(), "x").preliminary is True

def test_parse_tolerates_fences_and_odd_values():
    f = parse_facts('```json\n{"responsive":"YES","can_walk":"maybe","trapped":"yes","injuries_reported":"leg","summary":"stuck"}\n```')
    assert f.responsive == "yes" and f.can_walk == "unknown" and f.trapped == "yes" and f.injuries_reported == ["leg"]
    f = parse_facts('Here you go: {"responsive": "no"} thanks'); assert f.responsive == "no"

@pytest.mark.parametrize("bad", ["", "not json", "[1,2]", "{broken"])
def test_parse_rejects_garbage(bad):
    with pytest.raises(Exception): parse_facts(bad)
