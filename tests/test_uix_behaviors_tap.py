from textwrap import dedent
from contextlib import closing

import pytest

from kivy.tests.common import UnitTestTouch
import asynckivy as ak
from kivyx.uix.behaviors.tap import TapGestureRecognizer


KV = '''
Widget:
    Widget:
        id: target
        pos: 0, 0
        size: 100, 100
'''


def test_initial_state_of_target_widget(kivy_runner):
    kr = kivy_runner
    tree = kr.builder.load_string(KV)
    kr.window.add_widget(tree)
    kr.advance_frame()
    w = tree.ids.target
    assert w.pos == [0, 0]
    assert w.size == [100, 100]


@pytest.mark.parametrize("track_multiple_touches", [False, True])
def test__inside_touch_down__inside_touch_up(kivy_runner, track_multiple_touches):
    kr = kivy_runner
    event_log = []
    tree = kr.builder.load_string(KV)
    kr.window.add_widget(tree)
    kr.advance_frame()
    w = tree.ids.target
    rcg = TapGestureRecognizer(track_multiple_touches=track_multiple_touches)
    rcg.fbind("on_tap", lambda *args: event_log.extend(args))
    with closing(ak.start(rcg.enable_on(w))):
        kr.advance_frame()
        t = UnitTestTouch(50, 50)
        assert event_log == []
        t.touch_down()
        assert event_log == []
        t.touch_up()
        assert event_log == [rcg, w, t]


@pytest.mark.parametrize("track_multiple_touches", [False, True])
def test__inside_touch_down__outside_touch_up(kivy_runner, track_multiple_touches):
    kr = kivy_runner
    event_log = []
    tree = kr.builder.load_string(KV)
    kr.window.add_widget(tree)
    kr.advance_frame()
    w = tree.ids.target
    rcg = TapGestureRecognizer(track_multiple_touches=track_multiple_touches)
    rcg.fbind("on_tap", lambda *args: event_log.extend(args))
    with closing(ak.start(rcg.enable_on(w))):
        kr.advance_frame()
        t = UnitTestTouch(50, 50)
        assert event_log == []
        t.touch_down()
        assert event_log == []
        t.touch_move(150, 50)
        assert event_log == []
        t.touch_up()
        assert event_log == []


@pytest.mark.parametrize("track_multiple_touches", [False, True])
def test__outside_touch_down__inside_touch_up(kivy_runner, track_multiple_touches):
    kr = kivy_runner
    event_log = []
    tree = kr.builder.load_string(KV)
    kr.window.add_widget(tree)
    kr.advance_frame()
    w = tree.ids.target
    rcg = TapGestureRecognizer(track_multiple_touches=track_multiple_touches)
    rcg.fbind("on_tap", lambda *args: event_log.extend(args))
    with closing(ak.start(rcg.enable_on(w))):
        kr.advance_frame()
        t = UnitTestTouch(150, 50)
        assert event_log == []
        t.touch_down()
        assert event_log == []
        t.touch_move(50, 50)
        assert event_log == []
        t.touch_up()
        assert event_log == []


@pytest.mark.parametrize("track_multiple_touches", [False, True])
def test__outside_touch_down__outside_touch_up(kivy_runner, track_multiple_touches):
    kr = kivy_runner
    event_log = []
    tree = kr.builder.load_string(KV)
    kr.window.add_widget(tree)
    kr.advance_frame()
    w = tree.ids.target
    rcg = TapGestureRecognizer(track_multiple_touches=track_multiple_touches)
    rcg.fbind("on_tap", lambda *args: event_log.extend(args))
    with closing(ak.start(rcg.enable_on(w))):
        kr.advance_frame()
        t = UnitTestTouch(150, 50)
        assert event_log == []
        t.touch_down()
        assert event_log == []
        t.touch_up()
        assert event_log == []


@pytest.mark.parametrize("track_multiple_touches", [True, False])
def test__multi_touch(kivy_runner, track_multiple_touches):
    kr = kivy_runner
    event_log = []
    tree = kr.builder.load_string(KV)
    kr.window.add_widget(tree)
    kr.advance_frame()
    w = tree.ids.target.__self__
    rcg = TapGestureRecognizer(track_multiple_touches=track_multiple_touches)
    rcg.fbind("on_tap", lambda *args: event_log.extend(args))
    with closing(ak.start(rcg.enable_on(w))):
        kr.advance_frame()
        t1 = UnitTestTouch(20, 20)
        assert event_log == []
        t1.touch_down()
        assert event_log == []
        t2 = UnitTestTouch(50, 50)
        t2.touch_down()
        assert event_log == []
        t1.touch_up()
        assert event_log == [rcg, w, t1]
        event_log.clear()
        t2.touch_up()
        if track_multiple_touches:
            assert event_log == [rcg, w, t2]
        else:
            assert event_log == []


@pytest.mark.parametrize("track_multiple_touches", [True, False])
@pytest.mark.parametrize("consume_touch", [True, False])
def test__overlapping_widgets(kivy_runner, consume_touch, track_multiple_touches):
    kr = kivy_runner
    event_log = []

    def on_tap(*args):
        event_log.extend(args)
    tree = kr.builder.load_string(dedent('''
        Widget:
            Widget:
                id: bottom
                pos: 0, 0
                size: 100, 100
            Widget:
                id: top
                pos: 50, 50
                size: 100, 100
        '''))
    kr.window.add_widget(tree)
    kr.advance_frame()
    top = tree.ids.top.__self__
    bottom = tree.ids.bottom.__self__
    rcg = TapGestureRecognizer(
        track_multiple_touches=track_multiple_touches,
        consume_touch=consume_touch,
    )
    rcg.fbind("on_tap", lambda *args: event_log.extend(args))
    with (
        closing(ak.start(rcg.enable_on(top))),
        closing(ak.start(rcg.enable_on(bottom))),
    ):
        kr.advance_frame()
        t = UnitTestTouch(75, 75)
        assert event_log == []
        t.touch_down()
        assert event_log == []
        t.touch_up()
        assert event_log == [rcg, top if consume_touch else bottom, t]
        event_log.clear()

        t = UnitTestTouch(25, 25)
        assert event_log == []
        t.touch_down()
        assert event_log == []
        t.touch_up()
        assert event_log == [rcg, bottom, t]
        event_log.clear()

        t = UnitTestTouch(125, 125)
        assert event_log == []
        t.touch_down()
        assert event_log == []
        t.touch_up()
        assert event_log == [rcg, top, t]
        event_log.clear()
