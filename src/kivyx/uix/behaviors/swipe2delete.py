'''
https://youtu.be/4AHhps6GPbU
'''
__all__ = ("enable_swipe2delete", )
from typing import Literal
from functools import partial

from kivy.metrics import dp
from kivy.core.window import Window
from kivy.graphics import Translate
import asynckivy as ak

from kivyx.touch_filters import is_opos_colliding


def remove_child(layout, child):
    layout.remove_widget(child)


async def enable_swipe2delete(
    target_layout, /, *, delete_action=remove_child, swipe_threshold=dp(20), delete_threshold=dp(300),
    direction: Literal["horizontal", "vertical"]="horizontal",
):
    '''
    Enables swipe-to-delete functionality for a layout.

    :param delete_action: A callable that defines the actual deletion behavior.
    :param swipe_threshold: The minimum distance a touch must travel to be recognized as a swipe gesture.
    :param delete_threshold: The minimum distance a swipe gesture must travel to trigger the ``delete_action``
                             upon release.

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
        ox, __ = target.to_window(*touch.opos)
        exclusive_access = touch.ud["kivyx_exclusive_access"]

        # Waits until the touch travels beyond the swipe threshold.
        async with (
            ak.move_on_when(exclusive_access.wait_for_someone_to_claim()),
            ak.event_freq(Window, "on_touch_move", filter=is_the_same_touch) as on_touch_move,
        ):
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

        if exclusive_access.has_been_claimed:
            continue
        exclusive_access.claim()

        orig_opacity = c.opacity
        try:
            # Moves and changes the opacity of the child during swipe.
            with ak.transform(c, use_outer_canvas=True) as ig:
                ig.add(translate := Translate())
                async with (
                    ak.move_on_when(touch.ud["kivyx_end"].wait()),
                    ak.event_freq(Window, "on_touch_move", filter=is_the_same_touch) as on_touch_move,
                ):
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

            if abs(diff) > delete_threshold:
                delete_action(target, c)
        finally:
            c.opacity = orig_opacity
