import pytest
from audio import occlusion_mixer as mod

CASES = [
    ("occlusion_clear", "m.occlusion_gain(0, 4) == approx(1.0)"),
    ("occlusion_blocked", "m.occlusion_gain(4, 4) == approx(0.0)"),
    ("portal_same", "m.portal_gain('a', 'a', {}) == approx(1.0)"),
    ("portal_connected", "m.portal_gain('a', 'b', {'a': ['b'], 'b': ['a']}) == approx(1.0)"),
    ("portal_blocked", "m.portal_gain('a', 'c', {'a': ['b']}) == approx(0.0)"),
    ("reverb_inside", "m.reverb_fade(0.0, 10.0) == approx(1.0)"),
    ("reverb_edge", "m.reverb_fade(10.0, 10.0) == approx(0.0)"),
    ("doppler_approach", "m.doppler_pitch((1.0, 0.0), (0.0, 0.0)) > 1.0"),
    ("doppler_recede", "m.doppler_pitch((-1.0, 0.0), (0.0, 0.0)) < 1.0"),
    ("voice_priority", "m.bus_priority(5, 2) is True"),
    ("ambient_priority", "m.bus_priority(1, 4) is False"),
    ("dedupe_new", "m.dedupe_event(7, {1, 2}) is True"),
    ("dedupe_old", "m.dedupe_event(7, {7}) is False"),
    ("preload_ok", "m.preload_ready(2.0, 1.0) is True"),
    ("preload_late", "m.preload_ready(0.5, 1.0) is False")
]

@pytest.mark.parametrize("name,expr", CASES, ids=[c[0] for c in CASES])
def test_contract(name, expr):
    assert eval(expr, {"m": mod, "approx": pytest.approx})
