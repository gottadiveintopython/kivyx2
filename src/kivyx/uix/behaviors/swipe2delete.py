'''
===============
Swipe-to-Delete
===============

The swipe2delete module provides two ways to add swipe-to-delete functionality to layouts.

* :class:`KXSwipe2DeleteBehavior` is an ordinary Kivy behavior class that allows you to enable,
  disable and configure the functionality dynamically through Kivy properties.
* :func:`enable_swipe2delete` is an async function that enables the functionality for a specific
  instance rather than to an entire class.

`YouTube Demo <https://youtu.be/4AHhps6GPbU>`__
'''
__all__ = ("enable_swipe2delete", "KXSwipe2DeleteBehavior", )
from typing import Literal
from functools import partial

from kivy.metrics import dp
from kivy.properties import NumericProperty, BooleanProperty, OptionProperty
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Translate
import asynckivy as ak

from kivyx.touch_filters import is_opos_colliding

default_swipe_threshold = dp(20)
default_delete_threshold = dp(300)


def remove_child(layout, child):
    layout.remove_widget(child)


async def enable_swipe2delete(
    target_layout, /, *, delete_action=remove_child, swipe_threshold=default_swipe_threshold,
    delete_threshold=default_delete_threshold, direction: Literal["horizontal", "vertical"]="horizontal",
):
    '''
    Enables swipe-to-delete functionality for a layout.

    :param delete_action: A callable that defines the actual deletion behavior.
    :param swipe_threshold: The minimum distance a touch must travel to be recognized as a swipe gesture.
    :param delete_threshold: The minimum distance a swipe gesture must travel to trigger the ``delete_action``
                             upon release.

    .. code-block::

        import asynckivy as ak
        from kivyx.uix.behaviors.swipe2delete import enable_swipe2delete

        ak.managed_start(enable_swipe2delete(a_layout))

    The effect of this function persists until the returned coroutine is cancelled.
    '''
    abs = __builtins__["abs"]
    target = target_layout.__self__
    on_touch_down = partial(ak.event, target, "on_touch_down", filter=is_opos_colliding)
    while True:
        __, touch = await on_touch_down()
        ox, oy = target.to_local(*touch.opos)
        for c in target.children:
            if c.collide_point(ox, oy):
                break
        else:
            continue

        def is_the_same_touch(w, t, touch=touch):
            return t is touch
        ox, oy = target.to_window(*touch.opos)
        e_access = touch.ud["kivyx_exclusive_access"]

        async with (
            ak.move_on_when(touch.ud["kivyx_end_event"].wait()),
            ak.event_freq(Window, "on_touch_move", filter=is_the_same_touch) as on_touch_move,
        ):
            # Waits until the touch travels beyond the swipe threshold.
            async with ak.move_on_when(e_access.wait_for_someone_to_claim()):
                if direction == "horizontal":
                    while True:
                        await on_touch_move()
                        if abs(touch.x - ox) > swipe_threshold:
                            break
                elif direction == "vertical":
                    while True:
                        await on_touch_move()
                        if abs(touch.y - oy) > swipe_threshold:
                            break
                else:
                    raise ValueError(f"Invalid direction: {direction!r}")

            if e_access.has_been_claimed:
                continue
            e_access.claim()

            # Moves and changes the opacity of the child during swipe.
            orig_opacity = c.opacity
            diff = 0.
            try:
                with ak.transform(c, use_outer_canvas=True) as ig:
                    ig.add(translate := Translate())
                    fade_threshold = delete_threshold * 1.4
                    if direction == "horizontal":
                        while True:
                            await on_touch_move()
                            translate.x = diff = touch.x - ox
                            c.opacity = (1.0 - abs(diff) / fade_threshold) * orig_opacity
                    else:
                        while True:
                            await on_touch_move()
                            translate.y = diff = touch.y - oy
                            c.opacity = (1.0 - abs(diff) / fade_threshold) * orig_opacity
            finally:
                c.opacity = orig_opacity
                if abs(diff) > delete_threshold:
                    delete_action(target, c)


class KXSwipe2DeleteBehavior:
    '''
    A mix-in class that adds swipe-to-delete functionality to layouts.
    '''

    s2d_disabled = BooleanProperty(False)
    '''If either of ``disabled`` or :attr:`s2d_disabled` is ``True``,
    the swipe-to-delete functionality is disabled. '''

    s2d_swipe_threshold = NumericProperty(default_swipe_threshold)
    '''The minimum distance a touch must travel to be recognized as a swipe gesture. '''

    s2d_delete_threshold = NumericProperty(default_delete_threshold)
    '''The minimum distance a swipe gesture must travel to trigger an ``on_swipe2delete`` event upon release. '''

    s2d_direction = OptionProperty("horizontal", options=("horizontal", "vertical", ))


    def on_swipe2delete(self, layout, child):
        layout.remove_widget(child)

    def __init__(self, **kwargs):
        self.__main_task = ak.dummy_task
        self.register_event_type("on_swipe2delete")
        super().__init__(**kwargs)
        t = Clock.schedule_once(self.__reset)
        f = self.fbind
        f("disabled", t)
        f("parent", t)
        f("s2d_disabled", t)
        f("s2d_swipe_threshold", t)
        f("s2d_delete_threshold", t)
        f("s2d_direction", t)

    # Python's name mangling is weird. This method cannot be named '__reset'.
    def _KXSwipe2DeleteBehavior__reset(self, __):
        self.__main_task.cancel()
        if (self.parent is None) or self.disabled or self.s2d_disabled:
            return
        self.__main_task = ak.managed_start(enable_swipe2delete(
            self,
            swipe_threshold=self.s2d_swipe_threshold,
            delete_threshold=self.s2d_delete_threshold,
            direction=self.s2d_direction,
            delete_action=partial(self.dispatch, "on_swipe2delete"),
        ))
