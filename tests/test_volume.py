import pytest
from app.volume import VolumeService

@pytest.mark.parametrize("start,expected", [(150,100), (-10,0), (50,50)])
def test_initial_percent_clamped(start, expected):
    v = VolumeService(initial_percent=start)
    assert v.get_percent() == expected

def test_increase_decrease_bounds():
    v = VolumeService(initial_percent=95)
    v.increase()
    assert v.get_percent() == 100
    v.increase()
    assert v.get_percent() == 100
    v.decrease(step=200)
    assert v.get_percent() == 0
    v.decrease()
    assert v.get_percent() == 0

def test_mute_unmute_restores():
    v = VolumeService(initial_percent=70)
    v.mute()
    assert v.get_percent() == 0
    restored = v.unmute()
    assert restored == pytest.approx(70, rel=0.02)

def test_unmute_default_when_no_last():
    v = VolumeService(initial_percent=0)
    v.mute()
    restored = v.unmute(default_percent=55)
    assert restored == 55

def test_multiple_mute_unmute_sequence():
    v = VolumeService(initial_percent=60)
    v.mute(); v.mute()  # idempotente
    assert v.get_percent() == 0
    r1 = v.unmute()
    assert r1 == pytest.approx(60, rel=0.02)
    v.increase(step=15)  # 75
    v.mute()
    r2 = v.unmute()
    assert r2 == pytest.approx(75, rel=0.02)

def test_increase_after_mute_restores_last_non_zero():
    v = VolumeService(initial_percent=40)
    v.mute()
    assert v.get_percent() == 0
    v.increase(step=20)  # lógico -> 20
    # unmute deve usar novo last_non_zero se >0
    r = v.unmute()
    assert r >= 20
