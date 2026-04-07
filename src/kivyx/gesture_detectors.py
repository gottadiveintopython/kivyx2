'''
This module provides detectors for commonly used single-touch gestures.
They are expected to be raced with ``touch.ud["kivyx_end"].wait()``, for example:

.. code-block::

    import asynckivy as ak

    tasks = await ak.wait_any(
        touch.ud["kivyx_end"].wait(),
        long_press(touch),
        horizontal_swipe(touch),
    )
    if tasks[1].finished:
        print("Long press detected!")
    elif tasks[2].finished:
        print("Horizontal swipe detected!")
'''

__all__ = (
    "GestureDetector",
    "direction_free_swipe",
    "downward_swipe",
    "horizontal_swipe",
    "immediate",
    "leftward_swipe",
    "long_press",
    "rightward_swipe",
    "upward_swipe",
    "vertical_swipe",
)

from typing import TypeAlias
from collections.abc import Awaitable, Callable

from kivy.metrics import dp
from kivy.input.motionevent import MotionEvent
from kivy.core.window import Window
import asynckivy as ak

GestureDetector: TypeAlias = Callable[[MotionEvent], Awaitable]


async def immediate(touch):
    pass


def long_press(touch, *, min_duration=0.2):
    return ak.sleep(min_duration)


async def horizontal_swipe(touch, *, min_movement=dp(20)):
    async with ak.event_freq(Window, "on_touch_move", filter=lambda w, t, touch=touch: t is touch) as on_touch_move:
        movement = 0.
        neg_min = -min_movement
        while neg_min < movement < min_movement:
            await on_touch_move()
            movement += touch.dx


async def vertical_swipe(touch, *, min_movement=dp(20)):
    async with ak.event_freq(Window, "on_touch_move", filter=lambda w, t, touch=touch: t is touch) as on_touch_move:
        movement = 0.
        neg_min = -min_movement
        while neg_min < movement < min_movement:
            await on_touch_move()
            movement += touch.dy


async def rightward_swipe(touch, *, min_movement=dp(20)):
    async with ak.event_freq(Window, "on_touch_move", filter=lambda w, t, touch=touch: t is touch) as on_touch_move:
        movement = 0.
        while movement < min_movement:
            await on_touch_move()
            movement += touch.dx


async def upward_swipe(touch, *, min_movement=dp(20)):
    async with ak.event_freq(Window, "on_touch_move", filter=lambda w, t, touch=touch: t is touch) as on_touch_move:
        movement = 0.
        while movement < min_movement:
            await on_touch_move()
            movement += touch.dy


async def leftward_swipe(touch, *, min_movement=dp(20)):
    async with ak.event_freq(Window, "on_touch_move", filter=lambda w, t, touch=touch: t is touch) as on_touch_move:
        movement = 0.
        neg_min = -min_movement
        while neg_min < movement:
            await on_touch_move()
            movement += touch.dx


async def downward_swipe(touch, *, min_movement=dp(20)):
    async with ak.event_freq(Window, "on_touch_move", filter=lambda w, t, touch=touch: t is touch) as on_touch_move:
        movement = 0.
        neg_min = -min_movement
        while neg_min < movement:
            await on_touch_move()
            movement += touch.dy


async def direction_free_swipe(touch, *, min_movement=dp(20)):
    async with ak.event_freq(Window, "on_touch_move", filter=lambda w, t, touch=touch: t is touch) as on_touch_move:
        movement_x = 0.
        movement_y = 0.
        neg_min = -min_movement
        while neg_min < movement_x < min_movement and neg_min < movement_y < min_movement:
            await on_touch_move()
            movement_x += touch.dx
            movement_y += touch.dy
