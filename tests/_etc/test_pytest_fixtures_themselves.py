from functools import partial
import pytest


@pytest.mark.parametrize("n", range(2))
def test_isolate_builder_and_factory(isolate_builder_and_factory, n):
    from kivy.factory import Factory
    from kivy.lang import Builder
    assert "MyyWidget" not in Factory.classes
    Builder.load_string("<MyyWidget@ButtonBehavior+Label>:")
    assert "MyyWidget" in Factory.classes


def test_clock(kivy_runner):
    kr = kivy_runner
    approx = partial(pytest.approx, abs=1e-2)
    call_log = []
    kr.clock.schedule_once(call_log.append, 1)
    assert call_log == []
    kr.advance_a_frame(dt=0.7)
    assert call_log == []
    kr.advance_a_frame(dt=0.7)
    assert call_log == approx([1.4])
