__all__ = ("enable_tap_gesture_recognition", "KXTapGestureRecognizer", )
from typing import Any
from collections.abc import Callable
from functools import partial
from contextlib import nullcontext

from kivy.clock import Clock
from kivy.properties import ObjectProperty, BooleanProperty
from kivy.input.motionevent import MotionEvent
from kivy.uix.widget import Widget

import asynckivy as ak

from kivyx.touch_filters import is_colliding_and_not_wheel


class defaults:
    consume_touch = False
    track_multiple_touches = False


async def enable_tap_gesture_recognition(
    widget, *,
    track_multiple_touches=defaults.track_multiple_touches,
    touch_filter: Callable[[Widget, MotionEvent], bool]=is_colliding_and_not_wheel,
    consume_touch: bool=defaults.consume_touch,
    on_tap: Callable[[Widget, MotionEvent], Any]=print,
):
    '''
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
        Called on each successful tap gesture recognition.
        For its parameters, see :meth:`KXTapGestureRecognizer.on_tap`.
    '''
    on_touch_down = partial(ak.event, widget, "on_touch_down", filter=touch_filter, stop_dispatching=consume_touch)
    handler = _handle_a_potential_tap_gesture
    with ak.suppress_event(widget, "on_touch_down", filter=touch_filter) if consume_touch else nullcontext():
        if track_multiple_touches:
            async with ak.open_nursery() as nursery:
                while True:
                    __, touch = await on_touch_down()
                    nursery.start(handler(on_tap, widget, touch))
        else:
            while True:
                __, touch = await on_touch_down()
                await handler(on_tap, widget, touch)


async def _handle_a_potential_tap_gesture(on_tap, widget, touch):
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


class KXTapGestureRecognizer:
    '''
    A mixin class that adds tap gesture recognition capability to widgets.

    (Some docstrings in this class are written in Japanese because the corresponding English
    documentation is already available in :func:`enable_tap_gesture_recognition`.)
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

    tap_track_multiple_touches = BooleanProperty(defaults.track_multiple_touches)
    '''
    タッチを複数同時に監視するか否か。
    False(既定値)の場合、一つのタッチを監視している間に始まった他のタッチは無視される。
    '''

    def on_tap(self, touch):
        '''
        Fired on each successful tap gesture recognition.

        :param touch: The :class:`~kivy.input.motionevent.MotionEvent` instance that triggered the
            ``on_tap`` event, in window coordinates.
        '''

    def __init__(self, **kwargs):
        self.__main_task = ak.dummy_task
        self.register_event_type("on_tap")
        super().__init__(**kwargs)
        t = Clock.schedule_once(self.__reset, -1)
        self.bind(
            disabled=t,
            tap_disabled=t,
            tap_touch_filter=t,
            tap_track_multiple_touches=t,
        )

    # Python's name mangling is weird. This method cannot be named '__reset'.
    def _KXTapGestureRecognizer__reset(self, __):
        self.__main_task.cancel()
        if self.disabled or self.tap_disabled:
            return
        self.__main_task = ak.managed_start(enable_tap_gesture_recognition(
            self,
            touch_filter=self.tap_touch_filter,
            track_multiple_touches=self.tap_track_multiple_touches,
            on_tap=self.__dispatch_on_tap_event,
        ))

    @staticmethod
    def __dispatch_on_tap_event(widget, touch):
        widget.dispatch("on_tap", touch)
