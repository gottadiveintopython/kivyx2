__all__ = ("enable_tap_gesture_recognition", "on_tap", )
from typing import Any
from collections.abc import Callable
from functools import partial
from contextlib import nullcontext

from kivy.input.motionevent import MotionEvent
from kivy.uix.widget import Widget

import asynckivy as ak

from kivyx.touch_filters import is_colliding_and_not_wheel


async def enable_tap_gesture_recognition(
    widget, *,
    track_multiple_touches=False,
    touch_filter: Callable[[Widget, MotionEvent], bool]=is_colliding_and_not_wheel,
    consume_touch=True,
    on_tap: Callable[[Widget, MotionEvent], Any]=print,
):
    """
    Enables tap gesture recognition for a widget until the returned coroutine is cancelled.

    :param track_multiple_touches:
        Whether to track multiple touches simultaneously (multi-touch). If False (the default),
        once a touch starts being tracked, subsequent touches are ignored until the tracked touch
        ends or exclusive access to it is claimed by someone else.

    :param touch_filter:
        Any touch whose ``on_touch_down`` event does not pass this filter is ignored.
        Defaults to :func:`~kivyx.touch_filters.is_colliding_and_not_wheel`.

    :param consume_touch:
        Whether to consume ``on_touch_down`` events that pass the ``touch_filter``.

    :param on_tap:
        Called each time a tap gesture is successfully recognized.
        See :func:`on_tap` for the callback parameters.
    """
    on_touch_down = partial(ak.event, widget, "on_touch_down", filter=touch_filter, stop_dispatching=consume_touch)
    watch_for_release = _watch_for_release
    with ak.suppress_event(widget, "on_touch_down", filter=touch_filter) if consume_touch else nullcontext():
        if track_multiple_touches:
            async with ak.open_nursery() as nursery:
                while True:
                    __, touch = await on_touch_down()
                    nursery.start(watch_for_release(on_tap, widget, touch))
        else:
            while True:
                __, touch = await on_touch_down()
                await watch_for_release(on_tap, widget, touch)


async def _watch_for_release(on_tap, widget, touch):
    ud = touch.ud
    ex_access = ud["kivyx_exclusive_access"]
    tasks = await ak.wait_any(
        ud["kivyx_end"].wait(),
        ud["kivyx_abandon"].wait(),
        ex_access.wait_for_one_to_claim(),
    )
    if ex_access.has_been_claimed or tasks[1].finished:
        return
    if widget.collide_point(*widget.parent.to_widget(*touch.pos)):
        ex_access.claim(widget, "tap")
        on_tap(widget, touch)


def on_tap(widget, touch):
    '''
    :param widget:
        The widget instance that was tapped.

    :param touch:
        The :class:`~kivy.input.motionevent.MotionEvent` instance that triggered the tap,
        represented in window coordinates.
    '''
