# NOTE: max_distance を実装する場合は。 max_distance より遠い所でタッチが起きた時にそれを
# 別のマルチタップとして認識させるか否かを決めないといけない。させる場合の実装がおそらくかなり複
# 雑になるため現時点では実装しないことにした。


__all__ = ("enable_multi_tap_gesture_recognition", "on_multi_tap", )
from typing import Any
from collections.abc import Callable, Sequence
from contextlib import closing

from kivy.input.motionevent import MotionEvent
from kivy.uix.widget import Widget

import asynckivy as ak

from kivyx.touch_filters import is_colliding_and_not_wheel
from kivyx.utils import CancellableTimer
from .tap import enable_tap_gesture_recognition


async def enable_multi_tap_gesture_recognition(
    widget, *,
    touch_filter: Callable[[Widget, MotionEvent], bool]=is_colliding_and_not_wheel,
    consume_touch=True,
    max_time_interval=0.3,
    max_count=2,
    on_multi_tap: Callable[[Widget, int, Sequence[MotionEvent]], Any]=print,
):
    '''
    Enables multi-tap gesture recognition for a widget until the returned coroutine is cancelled.

    :param touch_filter:
        Any touch whose ``on_touch_down`` event does not pass this filter is ignored.
        Defaults to :func:`~kivyx.touch_filters.is_colliding_and_not_wheel`.

    :param consume_touch:
        Whether to consume ``on_touch_down`` events that pass the ``touch_filter``.

    :param max_time_interval:
        The maximum time interval allowed between taps to be considered part of the same multi-tap gesture.

    :param max_count:
        The maximum number of taps allowed in a multi-tap gesture.

    :param on_multi_tap:
        Called on each successful multi-tap gesture recognition.
        See :func:`on_multi_tap` for the callback parameters.
    '''
    tap_event = ak.ExclusiveEvent()
    timer = CancellableTimer(max_time_interval, event=ak.ExclusiveEvent())
    with closing(ak.start(enable_tap_gesture_recognition(
        widget,
        touch_filter=touch_filter,
        track_multiple_touches=True,
        consume_touch=consume_touch,
        on_tap=tap_event.fire,
    ))):
        while True:
            timer.cancel()
            __, touch = await tap_event.wait_args()
            accepted_touches = [touch, ]
            n_accepted = 1
            timer.start()
            async with ak.move_on_when(timer.wait_expiration()):
                while n_accepted < max_count:
                    __, touch = await tap_event.wait_args()
                    accepted_touches.append(touch)
                    n_accepted += 1
                    timer.cancel()
                    timer.start()
            on_multi_tap(widget, n_accepted, accepted_touches)


def on_multi_tap(widget, n_taps, touches):
    '''
    :param widget:
        The widget instance that was multi-tapped.

    :param n_taps:
        Equals to ``len(touches)``.

    :param touches:
        The :class:`~kivy.input.motionevent.MotionEvent` instances that triggered the multi-tap,
        represented in window coordinates, listed in the order in which they *ended* (not started).
    '''
