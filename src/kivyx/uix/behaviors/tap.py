__all__ = ("KXTapGestureRecognizer", "KXMultiTapGestureRecognizer", )

from collections.abc import Sequence
from functools import partial

from kivy.core.window import Window
from kivy.clock import Clock
from kivy.properties import BoundedNumericProperty, NumericProperty, ObjectProperty

import asynckivy as ak

from kivyx.touch_filters import is_opos_colliding, is_opos_colliding_and_not_wheel, is_colliding


class KXTapGestureRecognizer:
    '''
    A :class:`~kivy.uix.behaviors.button.ButtonBehavior` alternative for this library.
    '''

    tap_filter = ObjectProperty(is_opos_colliding_and_not_wheel)
    '''
    An ``on_touch_down`` event that does not pass this filter will immediately be disregarded as a tapping gesture.
    Defaults to :func:`~kivyx.touch_filters.is_opos_colliding_and_not_wheel`.
    '''

    def on_tap(self, touch):
        '''
        :param touch: The :class:`~kivy.input.motionevent.MotionEvent` instance that caused the ``on_tap`` event.
        '''

    def __init__(self, **kwargs):
        self.__main_task = ak.dummy_task
        self.register_event_type("on_tap")
        super().__init__(**kwargs)
        t = Clock.schedule_once(self.__reset)
        f = self.fbind
        f("disabled", t)
        f("parent", t)
        f("tap_filter", t)
        self.bind(on_touch_down=is_opos_colliding)

    # Python's name mangling is weird. This method cannot be named '__reset'.
    def _KXTapGestureRecognizer__reset(self, __):
        self.__main_task.cancel()
        if (self.parent is None) or self.disabled:
            return
        self.__main_task = ak.managed_start(self.__main())

    async def __main(self):
        touch = None
        on_touch_down = partial(ak.event, self, "on_touch_down", filter=self.tap_filter)
        on_touch_up = partial(ak.event, Window, "on_touch_up", filter=lambda w, t: t is touch)
        to_parent = self.parent.to_widget
        while True:
            __, touch = await on_touch_down()
            claim_signal = touch.ud["kivyx_claim_signal"]
            tasks = await ak.wait_any(claim_signal.wait(), on_touch_up())
            if tasks[0].finished:
                continue
            claim_signal.fire()
            # Because we received an on_touch_up event directly from the Window object,
            # we need to manually convert its coordinates.
            if self.collide_point(*to_parent(*touch.pos)):
                self.dispatch("on_tap", touch)


class KXMultiTapGestureRecognizer:
    tap_max_count = BoundedNumericProperty(2, min=1)
    tap_max_interval = NumericProperty(.3)
    tap_filter = ObjectProperty(is_opos_colliding_and_not_wheel)
    '''
    An ``on_touch_down`` event that does not pass this filter will immediately be disregarded as a tapping gesture.
    Defaults to :func:`~kivyx.touch_filters.is_opos_colliding_and_not_wheel`.
    '''

    def on_multi_tap(self, n_taps: int, touches: Sequence):
        '''
        :param n_taps: This equals to ``len(touches)``.
        :param touches: The :class:`~kivy.input.motionevent.MotionEvent` instances that caused the
                        ``on_multi_tap`` event. They are listed in the order they occurred.
        '''

    def __init__(self, **kwargs):
        self.__main_task = ak.dummy_task
        self.register_event_type("on_multi_tap")
        super().__init__(**kwargs)
        t = Clock.schedule_once(self.__reset)
        f = self.fbind
        f("disabled", t)
        f("parent", t)
        f("tap_max_count", t)
        f("tap_max_interval", t)
        f("tap_filter", t)
        self.bind(on_touch_down=is_opos_colliding)

    # Python's name mangling is weird. This method cannot be named '__reset'.
    def _KXMultiTapGestureRecognizer__reset(self, __):
        self.__main_task.cancel()
        if (self.parent is None) or self.disabled:
            return
        self.__main_task = ak.managed_start(self.__main())

    async def __main(self):
        touch = None
        on_touch_down = partial(ak.event, self, "on_touch_down", filter=self.tap_filter)
        on_touch_up = partial(ak.event, Window, "on_touch_up", filter=lambda w, t: t is touch)
        to_parent = self.parent.to_widget
        collide_point = self.collide_point
        timer = Timer(self.tap_max_interval)
        accepted_touches = []
        tap_max_count = self.tap_max_count
        while True:
            accepted_touches.clear()
            n_taps = 0
            timer.stop()
            async with ak.move_on_when(timer.wait_expiration()):
                while n_taps < tap_max_count:
                    __, touch = await on_touch_down()
                    timer.stop()
                    claim_signal = touch.ud["kivyx_claim_signal"]
                    tasks = await ak.wait_any(claim_signal.wait(), on_touch_up())
                    if tasks[0].finished:
                        break
                    claim_signal.fire()
                    # Because we received an on_touch_up event directly from the Window object,
                    # we need to manually convert its coordinates.
                    if collide_point(*to_parent(*touch.pos)):
                        n_taps += 1
                        accepted_touches.append(touch)
                        timer.start()
                    else:
                        break
            if n_taps:
                self.dispatch("on_multi_tap", n_taps, accepted_touches)


class Timer:
    __slots__ = ("wait_expiration", "start", "stop")

    def __init__(self, timeout: float):
        event = ak.ExclusiveEvent()
        ce = Clock.create_trigger(event.fire, timeout, False, False)
        self.wait_expiration = event.wait
        self.start = ce
        self.stop = ce.cancel
