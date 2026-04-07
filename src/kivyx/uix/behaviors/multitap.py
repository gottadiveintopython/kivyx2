# NOTE: max_distance を実装する場合は。 max_distance より遠い所でタッチが起きた時にそれを
# 別のマルチタップとして認識させるか否かを決めないといけない。させる場合の実装がおそらくかなり複
# 雑になるため現時点では実装しないことにした。


__all__ = ("enable_multi_tap_gesture_recognition", "KXMultiTapGestureRecognizer", )
from typing import Any
from collections.abc import Callable, Sequence
from contextlib import closing

from kivy.clock import Clock
from kivy.properties import ObjectProperty, BooleanProperty, BoundedNumericProperty, NumericProperty
from kivy.input.motionevent import MotionEvent
from kivy.uix.widget import Widget

import asynckivy as ak

from kivyx.touch_filters import is_colliding_and_not_wheel
from kivyx.utils import CancellableTimer
from .tap import enable_tap_gesture_recognition


class defaults:
    consume_touch = False
    max_time_interval = 0.3
    max_count = 2


async def enable_multi_tap_gesture_recognition(
    widget, *,
    touch_filter: Callable[[Widget, MotionEvent], bool]=is_colliding_and_not_wheel,
    consume_touch: bool=defaults.consume_touch,
    max_time_interval: float=defaults.max_time_interval,
    max_count: int=defaults.max_count,
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
        For its parameters, see :meth:`KXMultiTapGestureRecognizer.on_multi_tap`.
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


class KXMultiTapGestureRecognizer:
    '''
    A mixin class that adds multi-tap gesture recognition capability to widgets.

    (Some docstrings in this class are written in Japanese because the corresponding English
    documentation is already available in :func:`enable_multi_tap_gesture_recognition`.)
    '''

    tap_disabled = BooleanProperty(False)
    '''If either :attr:`~kivy.uix.widget.Widget.disabled` or :attr:`tap_disabled` is True,
    tap gesture recognition is disabled.
    '''

    tap_touch_filter = ObjectProperty(is_colliding_and_not_wheel)
    '''
    ``on_touch_down`` イベントがこの選別をくぐり抜けたタッチのみがタップとして認識され得る。
    既定値は :func:`~kivyx.touch_filters.is_colliding_and_not_wheel`。
    '''

    tap_max_count = BoundedNumericProperty(defaults.max_count, min=1)
    '''
    例えばこの値が2(既定値)の状態で三連続タップが起きた場合、最初の二回と最後の一回の二組のマルチタップとして認識される。
    '''

    tap_max_time_interval = NumericProperty(defaults.max_time_interval)
    '''
    あるタップが起きてから続いて起きたタップまでの経過時間がこの値以下であった場合に限りそれらが一組のマルチタップとして認識され得る。
    '''

    def on_multi_tap(self, n_taps: int, touches: Sequence):
        '''
        Fired on each successful multi-tap gesture recognition.

        :param n_taps: Equal to ``len(touches)``.
        :param touches: The :class:`~kivy.input.motionevent.MotionEvent` instances that triggered the ``on_multi_tap``
            event, in window coordinates, listed in the order in which they **ended** (not started).
        '''

    def __init__(self, **kwargs):
        self.__main_task = ak.dummy_task
        self.register_event_type("on_multi_tap")
        super().__init__(**kwargs)
        t = Clock.schedule_once(self.__reset, -1)
        self.bind(
            disabled=t,
            tap_disabled=t,
            tap_touch_filter=t,
            tap_max_count=t,
            tap_max_time_interval=t,
        )

    # Python's name mangling is weird. This method cannot be named '__reset'.
    def _KXMultiTapGestureRecognizer__reset(self, __):
        self.__main_task.cancel()
        if self.disabled or self.tap_disabled:
            return
        self.__main_task = ak.managed_start(enable_multi_tap_gesture_recognition(
            self,
            touch_filter=self.tap_touch_filter,
            max_count=self.tap_max_count,
            max_time_interval=self.tap_max_time_interval,
            on_multi_tap=self.__dispatch_on_multi_tap_event,
            ))

    @staticmethod
    def __dispatch_on_multi_tap_event(widget, n_taps, touches):
        widget.dispatch("on_multi_tap", n_taps, touches)
