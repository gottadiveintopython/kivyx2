from textwrap import dedent
from contextlib import closing

import pytest

from kivy.tests.common import UnitTestTouch
import asynckivy as ak
from kivyx.uix.behaviors.multitap import MultiTapGestureRecognizer


KV = '''
Widget:
    Widget:
        id: target
        pos: 0, 0
        size: 100, 100
'''


def test__triple_tap__max_count_2(kivy_runner):
    kr = kivy_runner
    event_log = []
    tree = kr.builder.load_string(KV)
    kr.window.add_widget(tree)
    kr.advance_a_frame()
    w = tree.ids.target
    rcg = MultiTapGestureRecognizer(max_count=2, max_time_interval=0.3)
    rcg.fbind("on_multi_tap", lambda *args: event_log.extend(args))
    with closing(ak.start(rcg.enable_on(w))):
        kr.advance_frame()
        t1 = UnitTestTouch(50, 50)
        t1.touch_down()
        t1.touch_up()
        assert event_log == []
        t2 = UnitTestTouch(50, 50)
        t2.touch_down()
        t2.touch_up()
        assert event_log == [rcg, w, 2, [t1, t2]]  # Event is fired without waiting for 3rd tap because max_count is 2.
        t3 = UnitTestTouch(50, 50)
        t3.touch_down()
        t3.touch_up()
        assert event_log == [rcg, w, 2, [t1, t2]]
        kr.advance_a_frame(dt=0.4)  # Let the internal timer expire
        assert event_log == [rcg, w, 2, [t1, t2], rcg, w, 1, [t3]]  # 3rd tap is treated as a separate multi-tap.


def test__double_tap__max_count_3(kivy_runner):
    kr = kivy_runner
    event_log = []
    tree = kr.builder.load_string(KV)
    kr.window.add_widget(tree)
    kr.advance_a_frame()
    w = tree.ids.target
    rcg = MultiTapGestureRecognizer(max_count=3, max_time_interval=0.3)
    rcg.fbind("on_multi_tap", lambda *args: event_log.extend(args))
    with closing(ak.start(rcg.enable_on(w))):
        kr.advance_frame()
        t1 = UnitTestTouch(50, 50)
        t1.touch_down()
        t1.touch_up()
        assert event_log == []
        t2 = UnitTestTouch(50, 50)
        t2.touch_down()
        t2.touch_up()
        assert event_log == []  # Still empty because the recognizer is waiting for 3rd tap
        kr.advance_a_frame(dt=0.4)  # Let the internal timer expire
        assert event_log == [rcg, w, 2, [t1, t2]]


def test_simultaneous_touches(kivy_runner):
    kr = kivy_runner
    event_log = []
    tree = kr.builder.load_string(KV)
    kr.window.add_widget(tree)
    kr.advance_a_frame()
    w = tree.ids.target
    rcg = MultiTapGestureRecognizer(max_count=2, max_time_interval=0.3)
    rcg.fbind("on_multi_tap", lambda *args: event_log.extend(args))
    with closing(ak.start(rcg.enable_on(w))):
        kr.advance_frame()
        t1 = UnitTestTouch(50, 50)
        t1.touch_down()
        kr.advance_a_frame(dt=0.1)
        t2 = UnitTestTouch(50, 50)
        t2.touch_down()
        t1.touch_up()
        assert event_log == []
        t2.touch_up()
        assert event_log == [rcg, w, 2, [t1, t2]]
        event_log.clear()
        kr.advance_a_frame(dt=0.4)  # Let the internal timer expire
        assert event_log == []
