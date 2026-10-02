# NOTE: max_distance を実装する場合は。 max_distance より遠い所でタッチが起きた時にそれを
# 別のマルチタップとして認識させるか否かを決めないといけない。させる場合の実装がおそらくかなり複
# 雑になるため現時点では実装しないことにした。


__all__ = ("MultiTapGestureRecognizer", )
from functools import partial
from collections.abc import Sequence
from contextlib import ExitStack

from kivy.event import EventDispatcher
from kivy.properties import ObjectProperty, BooleanProperty, BoundedNumericProperty, NumericProperty

import asynckivy as ak

from kivyx.touch_filters import is_colliding_and_not_wheel
from kivyx.utils import CancellableTimer
from .tap import TapGestureRecognizer


class MultiTapGestureRecognizer(EventDispatcher):
    """
    Enables multi-tap gesture recognition on a widget.

    .. code-block::

        import asynckivy as ak

        recognizer = MultiTapGestureRecognizer()
        ak.managed_start(recognizer.enable_on(widget))
        ...
        __, widget, touch = await ak.event(recognizer, "on_tap")
    """

    disabled = BooleanProperty(False)
    """
    If either :attr:`~kivy.uix.widget.Widget.disabled` or :attr:`disabled` is True,
    tap gesture recognition is disabled.
    """

    consume_touch = BooleanProperty(False)
    """
    Whether to consume ``on_touch_down`` events that pass the :attr:`touch_filter`.
    """

    touch_filter = ObjectProperty(is_colliding_and_not_wheel)
    """
    Any touch whose ``on_touch_down`` event does not pass this filter is ignored.
    Defaults to :func:`~kivyx.touch_filters.is_colliding_and_not_wheel`.
    """

    max_count = BoundedNumericProperty(2, min=1)
    """
    The maximum number of taps allowed in a multi-tap gesture.

    If this value is 2 and the user taps 3 times, the three taps are recognized as two separate
    multi-tap gestures: the first with 2 taps and the second with 1 tap.
    """

    max_time_interval = NumericProperty(0.3)
    """
    The maximum time interval allowed between taps to be considered part of the same multi-tap gesture.
    """

    __events__ = ("on_multi_tap", )

    def on_multi_tap(self, widget, n_taps: int, touches: Sequence):
        """
        Fired each time a multi-tap gesture is successfully recognized.

        :param widget:
            The widget instance that was multi-tapped.

        :param n_taps:
            Equals to ``len(touches)``.

        :param touches:
            The :class:`~kivy.input.motionevent.MotionEvent` instances that triggered the ``on_multi_tap`` event,
            represented in window coordinates, listed in the order in which they **ended** (not started).
        """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._tap_recognizer = recog = TapGestureRecognizer(
            track_multiple_touches=True,
        )
        ak.sync_attr((self, "disabled"), (recog, "disabled"), eager=True).__enter__()
        ak.sync_attr((self, "consume_touch"), (recog, "consume_touch"), eager=True).__enter__()
        ak.sync_attr((self, "touch_filter"), (recog, "touch_filter"), eager=True).__enter__()

    async def enable_on(self, widget):
        """
        Enables multi-tap gesture recognition on the given widget until the returned coroutine is cancelled.
        """
        with ExitStack() as stack:
            defer = stack.callback

            reset_event = ak.ExclusiveEvent()
            reset = reset_event.fire
            defer(self.unbind_uid, "max_time_interval", self.fbind("max_time_interval", reset))
            defer(ak.start(self._tap_recognizer.enable_on(widget)).cancel)

            on_tap = partial(ak.event, self._tap_recognizer, "on_tap")
            while True:
                await ak.sleep(-1)
                async with ak.move_on_when(reset_event.wait()):
                    timer = CancellableTimer(self.max_time_interval, event=ak.ExclusiveEvent())
                    while True:
                        timer.cancel()
                        *__, touch = await on_tap()
                        accepted_touches = [touch, ]
                        n_accepted = 1
                        timer.start()
                        async with ak.move_on_when(timer.wait_expiration()):
                            while n_accepted < self.max_count:
                                *__, touch = await on_tap()
                                accepted_touches.append(touch)
                                n_accepted += 1
                                timer.cancel()
                                timer.start()
                        self.dispatch("on_multi_tap", widget, n_accepted, accepted_touches)
