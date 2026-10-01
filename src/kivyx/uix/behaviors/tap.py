__all__ = ("TapGestureRecognizer", )
from functools import partial
from contextlib import nullcontext, ExitStack

from kivy.event import EventDispatcher
from kivy.properties import ObjectProperty, BooleanProperty

import asynckivy as ak

from kivyx.touch_filters import is_colliding_and_not_wheel


class TapGestureRecognizer(EventDispatcher):
    '''
    Enables tap gesture recognition on a widget.

    .. code-block::

        import asynckivy as ak

        recognizer = TapGestureRecognizer()
        ak.managed_start(recognizer.enable_on(widget))
        ...
        __, widget, touch = await ak.event(recognizer, "on_tap")
    '''

    disabled = BooleanProperty(False)
    '''If either :attr:`~kivy.uix.widget.Widget.disabled` or :attr:`disabled` is True,
    tap gesture recognition is disabled.
    '''

    touch_filter = ObjectProperty(is_colliding_and_not_wheel)
    '''
    Any touch whose ``on_touch_down`` event does not pass this filter is ignored.
    Defaults to :func:`~kivyx.touch_filters.is_colliding_and_not_wheel`.
    '''

    consume_touch = BooleanProperty(True)
    '''
    Whether to consume ``on_touch_down`` events that pass the :attr:`touch_filter`.
    '''

    track_multiple_touches = BooleanProperty(False)
    '''
    Whether to track multiple touches simultaneously (multi-touch). If False (the default),
    once a touch starts being tracked, subsequent touches are ignored until the tracked touch
    ends or exclusive access to it is claimed by someone else.
    '''

    __events__ = ("on_tap", )

    def on_tap(self, widget, touch):
        '''
        Fired each time a tap gesture is successfully recognized.

        :param widget:
            The widget instance that was tapped.

        :param touch:
            The :class:`~kivy.input.motionevent.MotionEvent` instance that triggered the
            ``on_tap`` event (window coordinates).
        '''

    async def enable_on(self, widget):
        '''
        Enables tap gesture recognition on the given widget until the returned coroutine is cancelled.
        '''
        with ExitStack() as stack:
            defer = stack.callback

            reset_event = ak.ExclusiveEvent()
            reset = reset_event.fire
            defer(widget.unbind_uid, "disabled", widget.fbind("disabled", reset))
            self.bind(disabled=reset, touch_filter=reset, consume_touch=reset, track_multiple_touches=reset)
            defer(self.unbind, disabled=reset, touch_filter=reset, consume_touch=reset, track_multiple_touches=reset)

            while True:
                await ak.sleep(-1)
                async with ak.move_on_when(reset_event.wait()):
                    if self.disabled or widget.disabled:
                        await ak.sleep_forever()
                    await self._watch_for_touches(widget)
    
    async def _watch_for_touches(self, widget):
        on_touch_down = partial(ak.event, widget, "on_touch_down", filter=self.touch_filter, stop_dispatching=self.consume_touch)
        watch_for_release = self._watch_for_release
        with ak.suppress_event(widget, "on_touch_down", filter=self.touch_filter) if self.consume_touch else nullcontext():
            if self.track_multiple_touches:
                async with ak.open_nursery() as nursery:
                    while True:
                        __, touch = await on_touch_down()
                        nursery.start(watch_for_release(widget, touch))
            else:
                while True:
                    __, touch = await on_touch_down()
                    await watch_for_release(widget, touch)

    async def _watch_for_release(self, widget, touch):
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
            self.dispatch("on_tap", widget, touch)
