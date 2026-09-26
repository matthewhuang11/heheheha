from scoutbot.tools import distance_tune as dt

def test_suggest_midpoints():
    rows = {"0.7": [0.9], "1": [0.7, 0.72], "1.5": [0.5], "2.5": [0.3], "4": [0.18], "lying 1.5": [0.2]}
    near, mid = dt.suggest(rows)
    assert near == round((0.71 + 0.5) / 2, 3) and mid == round((0.3 + 0.18) / 2, 3)

def test_suggest_missing_distance():
    assert dt.suggest({"1": [0.7]}) == (None, None)

def test_parser_help():
    import pytest
    with pytest.raises(SystemExit) as e: dt.parser().parse_args(["--help"])
    assert e.value.code == 0
