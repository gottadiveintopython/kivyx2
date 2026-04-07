from textwrap import dedent
from contextlib import closing

import pytest

from kivy.tests.common import UnitTestTouch
import asynckivy as ak
from kivyx.utils import drop_active_touches
from kivyx.uix.behaviors.swipe2delete import (
    enable_swipe2delete,
    enable_swipe2delete_for_children,
    ongoing_swipe2deletes,
)

# NOTE: A touch must generate at least two `on_touch_move` events to trigger `on_delete_requested`:
# one to be recognized as a swipe gesture (exceeding `swipe_distance`), and another to trigger the
# delete request (exceeding `delete_distance`).


KV = '''
Widget:
    BoxLayout:
        id: layout
        orientation: "vertical"
        size: 400, 400
        Widget:
        Widget:
            id: target
'''


def test_initial_state_of_widget_tree(kivy_runner):
    kr = kivy_runner
    tree = kr.builder.load_string(KV)
    kr.window.add_widget(tree)
    kr.advance_a_frame()
    l = tree.ids.layout
    assert l.pos == [0, 0]
    assert l.size == [400, 400]
    assert len(l.children) == 2
    c = l.children[0]
    assert c.pos == [0, 0]
    assert c.size == [400, 200]
    c = l.children[1]
    assert c.pos == [0, 200]
    assert c.size == [400, 200]


@pytest.mark.parametrize("for_children", [True, False])
def test_a_touch_travels_less_than_swipe_distance(kivy_runner, for_children):
    kr = kivy_runner
    tree = kr.builder.load_string(KV)
    kr.window.add_widget(tree)
    kr.advance_a_frame()
    layout = tree.ids.layout
    if for_children:
        coro = enable_swipe2delete_for_children(layout, swipe_distance=100)
    else:
        coro = enable_swipe2delete(tree.ids.target, swipe_distance=100)
    with closing(ak.start(coro)):
        t = UnitTestTouch(50, 50)
        t.touch_down()
        t.touch_move(70, 50)
        t.touch_move(90, 50)
        t.touch_up()
        assert len(layout.children) == 2


@pytest.mark.parametrize("for_children", [True, False])
def test_a_touch_travels_more_than_swipe_distance_and_less_than_delete_distance(kivy_runner, for_children):
    kr = kivy_runner
    tree = kr.builder.load_string(KV)
    kr.window.add_widget(tree)
    kr.advance_a_frame()
    layout = tree.ids.layout
    if for_children:
        coro = enable_swipe2delete_for_children(layout, swipe_distance=100, delete_distance=200)
    else:
        coro = enable_swipe2delete(tree.ids.target, swipe_distance=100, delete_distance=200)
    with closing(ak.start(coro)):
        t = UnitTestTouch(50, 50)
        t.touch_down()
        t.touch_move(110, 50)
        t.touch_move(170, 50)
        t.touch_up()
        assert len(layout.children) == 2


@pytest.mark.parametrize("for_children", [True, False])
def test_a_touch_travels_more_than_delete_distance(kivy_runner, for_children):
    kr = kivy_runner
    tree = kr.builder.load_string(KV)
    kr.window.add_widget(tree)
    kr.advance_a_frame()
    layout = tree.ids.layout
    if for_children:
        coro = enable_swipe2delete_for_children(layout, swipe_distance=100, delete_distance=200)
    else:
        coro = enable_swipe2delete(tree.ids.target, swipe_distance=100, delete_distance=200)
    with closing(ak.start(coro)):
        t = UnitTestTouch(50, 50)
        t.touch_down()
        t.touch_move(110, 50)
        t.touch_move(170, 50)
        t.touch_move(230, 50)
        t.touch_move(290, 50)
        t.touch_up()
        assert len(layout.children) == 1


@pytest.mark.parametrize("for_children", [True, False])
def test_a_touch_travels_more_than_delete_distance_perpendicular_to_swipe_direction(kivy_runner, for_children):
    kr = kivy_runner
    tree = kr.builder.load_string(KV)
    kr.window.add_widget(tree)
    kr.advance_a_frame()
    layout = tree.ids.layout
    if for_children:
        coro = enable_swipe2delete_for_children(layout, swipe_distance=100, delete_distance=200)
    else:
        coro = enable_swipe2delete(tree.ids.target, swipe_distance=100, delete_distance=200)
    with closing(ak.start(coro)):
        t = UnitTestTouch(50, 50)
        t.touch_down()
        t.touch_move(50, 110)
        t.touch_move(50, 170)
        t.touch_move(50, 230)
        t.touch_move(50, 290)
        t.touch_up()
        assert len(layout.children) == 2


@pytest.mark.parametrize("for_children", [True, False])
def test_multiple_touches_try_to_swipe_the_same_widget(kivy_runner, for_children):
    kr = kivy_runner
    tree = kr.builder.load_string(KV)
    kr.window.add_widget(tree)
    kr.advance_a_frame()
    layout = tree.ids.layout
    if for_children:
        coro = enable_swipe2delete_for_children(layout, swipe_distance=100, delete_distance=200, track_multiple_touches=True)
    else:
        coro = enable_swipe2delete(tree.ids.target, swipe_distance=100, delete_distance=200)
    with closing(ak.start(coro)):
        t1 = UnitTestTouch(50, 50)
        t2 = UnitTestTouch(50, 50)
        t1.touch_down()
        t2.touch_down()
        t1.touch_move(110, 50)
        t2.touch_move(110, 50)
        t1.touch_move(170, 50)

        # Since t1 has been recognized as a swipe gesture before t2, t2 has no effect at this point.

        t2.touch_move(170, 50)
        t2.touch_move(230, 50)
        t2.touch_move(290, 50)
        t2.touch_up()
        assert len(layout.children) == 2
        t1.touch_move(230, 50)
        t1.touch_move(290, 50)
        t1.touch_up()
        assert len(layout.children) == 1


def test_simultaneous_swipe2delete(kivy_runner):
    kr = kivy_runner
    tree = kr.builder.load_string(KV)
    kr.window.add_widget(tree)
    kr.advance_a_frame()
    layout = tree.ids.layout
    children = layout.children
    ongoing_ones = ongoing_swipe2deletes
    with closing(ak.start(enable_swipe2delete_for_children(layout, swipe_distance=100, delete_distance=200, track_multiple_touches=True))):
        t1 = UnitTestTouch(50, 50)
        t2 = UnitTestTouch(50, 250)
        t1.touch_down()
        t2.touch_down()
        assert ongoing_ones() == []
        t1.touch_move(110, 50)
        assert ongoing_ones() == []
        t2.touch_move(110, 250)
        assert ongoing_ones() == []
        t1.touch_move(170, 50)
        assert ongoing_ones() == [(children[0], t1), ]
        t2.touch_move(170, 250)
        assert ongoing_ones() == [(children[0], t1), (children[1], t2)]
        t1.touch_move(230, 50)
        assert ongoing_ones() == [(children[0], t1), (children[1], t2)]
        t2.touch_move(230, 250)
        assert ongoing_ones() == [(children[0], t1), (children[1], t2)]
        t1.touch_move(290, 50)
        assert ongoing_ones() == [(children[0], t1), (children[1], t2)]
        t2.touch_move(290, 250)
        assert ongoing_ones() == [(children[0], t1), (children[1], t2)]
        assert len(children) == 2
        t2.touch_up()
        assert ongoing_ones() == [(children[0], t1), ]
        assert len(children) == 1
        t1.touch_up()
        assert ongoing_ones() == []
        assert len(children) == 0


def test_cancel(kivy_runner):
    kr = kivy_runner
    tree = kr.builder.load_string(KV)
    kr.window.add_widget(tree)
    kr.advance_a_frame()
    layout = tree.ids.layout
    children = layout.children
    ongoing_ones = ongoing_swipe2deletes
    with closing(ak.start(enable_swipe2delete_for_children(layout, swipe_distance=100, delete_distance=200, track_multiple_touches=True))):
        t1 = UnitTestTouch(50, 50)
        t2 = UnitTestTouch(50, 250)
        t1.touch_down()
        t2.touch_down()
        t1.touch_move(110, 50)
        t2.touch_move(110, 250)
        t1.touch_move(170, 50)
        t2.touch_move(170, 250)
        t1.touch_move(230, 50)
        t2.touch_move(230, 250)
        t1.touch_move(290, 50)
        t2.touch_move(290, 250)
        assert ongoing_ones() == [(children[0], t1), (children[1], t2)]
        assert len(children) == 2
        t2.touch_up()
        assert ongoing_ones() == [(children[0], t1), ]
        assert len(children) == 1
        drop_active_touches()
        assert ongoing_ones() == []
        assert len(children) == 1
        t1.touch_up()  # This should have no effect since t1's swipe2delete gesture has been cancelled.
        assert ongoing_ones() == []
        assert len(children) == 1


def test_mixin_class(kivy_runner, isolate_builder_and_factory):
    kr = kivy_runner
    tree = kr.builder.load_string(dedent('''
        <MySwipe2Delete@KXSwipe2DeleteBehavior+BoxLayout>:
        Widget:
            MySwipe2Delete:
                id: layout
                size: 400, 400
                s2d_swipe_distance: 100
                s2d_delete_distance: 200
                Widget:
        '''))
    layout = tree.ids.layout
    kr.window.add_widget(tree)
    kr.advance_a_frame()
    assert len(layout.children) == 1
    t = UnitTestTouch(50, 50)
    t.touch_down()
    t.touch_move(110, 50)
    t.touch_move(170, 50)
    t.touch_move(230, 50)
    t.touch_move(290, 50)
    t.touch_up()
    assert len(layout.children) == 0
    ak.cancel_managed_tasks()
