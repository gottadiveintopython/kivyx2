from textwrap import dedent
from contextlib import closing

import pytest

from kivy.tests.common import UnitTestTouch
import asynckivy as ak
from kivyx.uix.behaviors.tap import enable_tap_gesture_recognition


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
    kr.advance_a_frame()
    w = tree.ids.target
    assert w.pos == [0, 0]
    assert w.size == [100, 100]


@pytest.mark.parametrize("track_multiple_touches", [False, True])
def test__inside_touch_down__inside_touch_up(kivy_runner, track_multiple_touches):
    kr = kivy_runner
    tap_event = ak.StatefulEvent()
    tree = kr.builder.load_string(KV)
    kr.window.add_widget(tree)
    kr.advance_a_frame()
    w = tree.ids.target
    with closing(ak.start(enable_tap_gesture_recognition(
            w, on_tap=tap_event.fire, track_multiple_touches=track_multiple_touches))):
        t = UnitTestTouch(50, 50)
        assert not tap_event.is_fired
        t.touch_down()
        assert not tap_event.is_fired
        t.touch_up()
        assert tap_event.is_fired
        assert tap_event.params[0] == (w, t)


@pytest.mark.parametrize("track_multiple_touches", [False, True])
def test__inside_touch_down__outside_touch_up(kivy_runner, track_multiple_touches):
    kr = kivy_runner
    tap_event = ak.StatefulEvent()
    tree = kr.builder.load_string(KV)
    kr.window.add_widget(tree)
    kr.advance_a_frame()
    w = tree.ids.target
    with closing(ak.start(enable_tap_gesture_recognition(
            w, on_tap=tap_event.fire, track_multiple_touches=track_multiple_touches))):
        t = UnitTestTouch(50, 50)
        assert not tap_event.is_fired
        t.touch_down()
        assert not tap_event.is_fired
        t.touch_move(150, 50)
        assert not tap_event.is_fired
        t.touch_up()
        assert not tap_event.is_fired


@pytest.mark.parametrize("track_multiple_touches", [False, True])
def test__outside_touch_down__inside_touch_up(kivy_runner, track_multiple_touches):
    kr = kivy_runner
    tap_event = ak.StatefulEvent()
    tree = kr.builder.load_string(KV)
    kr.window.add_widget(tree)
    kr.advance_a_frame()
    w = tree.ids.target
    with closing(ak.start(enable_tap_gesture_recognition(
            w, on_tap=tap_event.fire, track_multiple_touches=track_multiple_touches))):
        t = UnitTestTouch(150, 50)
        assert not tap_event.is_fired
        t.touch_down()
        assert not tap_event.is_fired
        t.touch_move(50, 50)
        assert not tap_event.is_fired
        t.touch_up()
        assert not tap_event.is_fired


@pytest.mark.parametrize("track_multiple_touches", [False, True])
def test__outside_touch_down__outside_touch_up(kivy_runner, track_multiple_touches):
    kr = kivy_runner
    tap_event = ak.StatefulEvent()
    tree = kr.builder.load_string(KV)
    kr.window.add_widget(tree)
    kr.advance_a_frame()
    w = tree.ids.target
    with closing(ak.start(enable_tap_gesture_recognition(
            w, on_tap=tap_event.fire, track_multiple_touches=track_multiple_touches))):
        t = UnitTestTouch(150, 50)
        assert not tap_event.is_fired
        t.touch_down()
        assert not tap_event.is_fired
        t.touch_up()
        assert not tap_event.is_fired


@pytest.mark.parametrize("track_multiple_touches", [True, False])
def test__multi_touch(kivy_runner, track_multiple_touches):
    kr = kivy_runner
    event_log = []
    tree = kr.builder.load_string(KV)
    kr.window.add_widget(tree)
    kr.advance_a_frame()
    w = tree.ids.target
    with closing(ak.start(enable_tap_gesture_recognition(
            w, on_tap=lambda *args: event_log.extend(args), track_multiple_touches=track_multiple_touches))):
        t1 = UnitTestTouch(20, 20)
        assert event_log == []
        t1.touch_down()
        assert event_log == []
        t2 = UnitTestTouch(50, 50)
        t2.touch_down()
        assert event_log == []
        t1.touch_up()
        assert event_log == [w, t1]
        event_log.clear()
        t2.touch_up()
        if track_multiple_touches:
            assert event_log == [w, t2]
        else:
            assert event_log == []


@pytest.mark.parametrize("track_multiple_touches", [True, False])
@pytest.mark.parametrize("consume_touch", [True, False])
def test__overlap(kivy_runner, consume_touch, track_multiple_touches):
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
    kr.advance_a_frame()
    top = tree.ids.top
    bottom = tree.ids.bottom
    with (
        closing(ak.start(enable_tap_gesture_recognition(
            top, on_tap=on_tap, consume_touch=consume_touch, track_multiple_touches=track_multiple_touches))),
        closing(ak.start(enable_tap_gesture_recognition(
            bottom, on_tap=on_tap, consume_touch=consume_touch, track_multiple_touches=track_multiple_touches))),
    ):
        t = UnitTestTouch(75, 75)
        assert event_log == []
        t.touch_down()
        assert event_log == []
        t.touch_up()
        assert event_log == [top if consume_touch else bottom, t]
        event_log.clear()

        t = UnitTestTouch(25, 25)
        assert event_log == []
        t.touch_down()
        assert event_log == []
        t.touch_up()
        assert event_log == [bottom, t]
        event_log.clear()

        t = UnitTestTouch(125, 125)
        assert event_log == []
        t.touch_down()
        assert event_log == []
        t.touch_up()
        assert event_log == [top, t]
        event_log.clear()


def test_mixin_class(kivy_runner, isolate_builder_and_factory):
    kr = kivy_runner
    tap_event = ak.StatefulEvent()
    tree = kr.builder.load_string(dedent('''
        <MyWidget@KXTapGestureRecognizer+Widget>:
        Widget:
            MyWidget:
                id: target
                pos: 0, 0
                size: 100, 100
        '''))
    w = tree.ids.target
    w.fbind("on_tap", tap_event.fire)
    kr.window.add_widget(tree)
    kr.advance_a_frame()
    t = UnitTestTouch(50, 50)
    assert not tap_event.is_fired
    t.touch_down()
    assert not tap_event.is_fired
    t.touch_up()
    assert tap_event.is_fired
    assert tap_event.params[0] == (w, t)
    ak.cancel_managed_tasks()
