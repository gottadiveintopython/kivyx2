'''
This module provides detectors for commonly used low-level single-touch gestures.
Detectors are intended to be raced against ``touch.ud["kivyx_end"].wait()``, for example:

.. code-block::

    from kivy.core.window import Window
    import asynckivy as ak

    tasks = await ak.wait_any(
        touch.ud["kivyx_end"].wait(),
        long_press(Window, touch),
        horizontal_swipe(Window, touch),
    )
    if tasks[1].finished:
        print("A long press gesture is detected")
    elif tasks[2].finished:
        print("A horizontal swipe gesture is detected")
    else:
        print("Touch ended before any gesture is detected")
'''

__all__ = (
    "GestureDetector",
    "horizontal_swipe",
    "immediate",
    "long_press",
    "vertical_swipe",
)
from typing import Any
from collections.abc import Callable, Awaitable
from os import environ

from kivy.metrics import dp
from kivy.input import MotionEvent
from kivy.core.window import WindowBase
from kivy.uix.widget import Widget
from asynckivy import sleep, event_freq

LONGPRESS_DURATION = float(environ.get("KIVYX_LONGPRESS_DURATION", 0.2))
SWIPE_DISTANCE = float(environ.get("KIVYX_SWIPE_DISTANCE", dp(20)))
type Wow = WindowBase | Widget
type GestureDetector = Callable[[Wow, MotionEvent], Awaitable[Any]]


async def immediate(receiver: Wow, touch):
    pass


def long_press(receiver: Wow, touch, *, min_duration=LONGPRESS_DURATION):
    '''
    :param min_duration:
        Minimum duration the ``touch`` must be held for to be recognized as a long press gesture.
    '''
    return sleep(min_duration)


async def horizontal_swipe(receiver: Wow, touch, *, min_distance=SWIPE_DISTANCE):
    '''
    :param min_distance:
        Minimum distance the ``touch`` must travel in the x direction to be recognized as a swipe gesture.
    '''
    with event_freq(receiver, "on_touch_move", filter=lambda w, t, touch=touch: t is touch) as on_touch_move:
        net_distance = 0.
        neg_min = -min_distance
        while neg_min < net_distance < min_distance:
            await on_touch_move()
            net_distance += touch.dx


async def vertical_swipe(receiver: Wow, touch, *, min_distance=SWIPE_DISTANCE):
    '''
    :param min_distance:
        Minimum distance the ``touch`` must travel in the y direction to be recognized as a swipe gesture.
    '''
    with event_freq(receiver, "on_touch_move", filter=lambda w, t, touch=touch: t is touch) as on_touch_move:
        net_distance = 0.
        neg_min = -min_distance
        while neg_min < net_distance < min_distance:
            await on_touch_move()
            net_distance += touch.dy
