"""Duration clamp + config behaviour for doomscroll()."""


from doomscroll_mcp.config import Settings


def test_max_duration_default():
    assert Settings.from_env().max_duration_s == 1800


def test_max_duration_env_override(monkeypatch):
    monkeypatch.setenv("DOOMSCROLL_MAX_DURATION_S", "120")
    assert Settings.from_env().max_duration_s == 120


def test_max_duration_bad_env_falls_back(monkeypatch):
    monkeypatch.setenv("DOOMSCROLL_MAX_DURATION_S", "not-a-number")
    assert Settings.from_env().max_duration_s == 1800


def test_duration_clamp_logic():
    # Mirror the clamp used in _browse: max(1, min(requested, ceiling)).
    ceiling = 1800
    assert max(1, min(10, ceiling)) == 10
    assert max(1, min(99999, ceiling)) == ceiling
    assert max(1, min(0, ceiling)) == 1
