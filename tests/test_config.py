import pytest

from doomscroll_mcp.config import MODES, HumanizeConfig, Settings


def test_fast_test_mode_is_near_instant():
    cfg = HumanizeConfig.for_mode("fast_test")
    assert cfg.scroll_delay_range[1] <= 0.1
    assert cfg.scroll_jitter is False


def test_conservative_mode_has_cap_and_cooldown():
    cfg = HumanizeConfig.for_mode("conservative")
    assert cfg.session_max_reels < HumanizeConfig().session_max_reels
    assert cfg.cooldown_after_session > 0


def test_likes_off_by_default():
    cfg = HumanizeConfig()
    assert cfg.enable_likes is False
    assert cfg.like_probability == 0.0


def test_unknown_mode_falls_back_to_normal(tmp_path):
    s = Settings(profile_dir=tmp_path / "p", fixtures_dir=tmp_path / "f")
    for m in MODES:
        assert s.with_mode(m).mode == m
    with pytest.raises(ValueError):
        s.with_mode("nope")
