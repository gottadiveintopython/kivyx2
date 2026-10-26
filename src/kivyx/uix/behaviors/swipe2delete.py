__all__ = (
    "enable_swipe2delete",
    "enable_swipe2delete_for_children",
    "disable_and_remove",
    "get_active_swipe2deletes",
)
from typing import Literal
from functools import partial
from collections.abc import Callable
from contextlib import AsyncExitStack

from kivy.metrics import dp
from kivy.base import EventLoop
from kivy.core.window import Window
from kivy.input.motionevent import MotionEvent
from kivy.uix.widget import Widget
from kivy.graphics import Translate
import asynckivy as ak

from kivyx.touch_filters import is_colliding_and_not_wheel
from kivyx.gesture_detectors import horizontal_swipe, vertical_swipe


def disable_and_remove(target, touch):
    '''
    Default action performed when a swipe-to-delete gesture requests deletion.

    .. code-block::

        def disable_and_remove(target, touch):
            target.disabled = True
            target.parent.remove_widget(target)
    '''
    target.disabled = True
    target.parent.remove_widget(target)


async def enable_swipe2delete_for_children(
    layout, /, *,
    touch_filter: Callable[[Widget, MotionEvent], bool]=is_colliding_and_not_wheel,
    direction: Literal["horizontal", "vertical"]="horizontal",
    swipe_distance=dp(20),
    delete_distance=dp(300),
    on_delete_requested: Callable[[Widget, MotionEvent], None]=disable_and_remove,
    track_multiple_touches=False,
):
    '''
    Enables swipe-to-delete functionality for a layout's children until the returned coroutine is cancelled.

    :param touch_filter:
        Any touch whose ``on_touch_down`` event does not pass this filter is ignored.
        Defaults to :func:`~kivyx.touch_filters.is_colliding_and_not_wheel`.

    :param direction:
        The swipe direction to detect.

    :param swipe_distance:
        The minimum distance a touch must travel to be recognized as a swipe gesture.
        Defaults to ``dp(20)``.

    :param delete_distance:
        The minimum distance a recognized swipe gesture must travel to trigger ``on_delete_requested``
        when the touch is released. Defaults to ``dp(300)``.

    :param on_delete_requested:
        A callable invoked when a delete request is triggered. Defaults to :func:`disable_and_remove`.

    :param track_multiple_touches:
        Whether to track multiple touches simultaneously (multi-touch). If False (the default),
        once a touch starts being tracked, subsequent touches are ignored until the tracked touch
        ends or exclusive access to it is claimed by someone else.
    '''
    from kivyx.utils import find_child_at

    match direction:
        case "horizontal":
            touch_handler = partial(
                _handle_potential_swipe2delete,
                True,
                partial(horizontal_swipe, min_movement=swipe_distance),
                delete_distance,
                on_delete_requested,
            )
        case "vertical":
            touch_handler = partial(
                _handle_potential_swipe2delete,
                False,
                partial(vertical_swipe, min_movement=swipe_distance),
                delete_distance,
                on_delete_requested,
            )
        case _:
           raise ValueError(f"Invalid direction: {direction!r}")

    layout = layout.__self__
    children = layout.children
    to_local = layout.to_local
    on_touch_down = partial(ak.event, layout, "on_touch_down", filter=touch_filter)

    if track_multiple_touches:
        async with ak.open_nursery() as nursery:
            while True:
                __, touch = await on_touch_down()
                child = find_child_at(children, *to_local(*touch.pos))
                if child is not None:
                    nursery.start(touch_handler(child, touch))
    else:
        while True:
            __, touch = await on_touch_down()
            child = find_child_at(children, *to_local(*touch.pos))
            if child is not None:
                await touch_handler(child, touch)


async def enable_swipe2delete(
    widget, /, *,
    touch_filter: Callable[[Widget, MotionEvent], bool]=is_colliding_and_not_wheel,
    direction: Literal["horizontal", "vertical"]="horizontal",
    swipe_distance=dp(20),
    delete_distance=dp(300),
    on_delete_requested: Callable[[Widget, MotionEvent], None]=disable_and_remove,
):
    '''
    Enables swipe-to-delete functionality for a widget until the returned coroutine is cancelled.

    See :func:`enable_swipe2delete_for_children` for the parameters.
    '''
    match direction:
        case "horizontal":
            touch_handler = partial(
                _handle_potential_swipe2delete,
                True,
                partial(horizontal_swipe, min_movement=swipe_distance),
                delete_distance,
                on_delete_requested,
            )
        case "vertical":
            touch_handler = partial(
                _handle_potential_swipe2delete,
                False,
                partial(vertical_swipe, min_movement=swipe_distance),
                delete_distance,
                on_delete_requested,
            )
        case _:
           raise ValueError(f"Invalid direction: {direction!r}")

    widget = widget.__self__
    on_touch_down = partial(ak.event, widget, "on_touch_down", filter=touch_filter)
    while True:
        __, touch = await on_touch_down()
        await touch_handler(widget, touch)


async def _handle_potential_swipe2delete(
    is_horizontal,
    swipe_detector,
    delete_distance,
    on_delete_requested,
    target: Widget,
    touch,
    _active_targets=[],
):
    '''
    Monitors the ``touch`` motion and performs swipe-to-delete on the ``target`` if a swipe gesture is detected.
    '''
    ex_access = touch.ud["kivyx_exclusive_access"]

    async with AsyncExitStack() as stack:
        defer = stack.callback
        await stack.enter_async_context(ak.move_on_when(touch.ud["kivyx_abandon"].wait()))
        tasks = await ak.wait_any(
            touch.ud["kivyx_end"].wait(),
            ex_access.wait_for_one_to_claim(),
            swipe_detector(touch),
        )
        if tasks[2].cancelled or target in _active_targets:
            return
        ex_access.claim(target, "swipe2delete")

        _active_targets.append(target)
        defer(_active_targets.remove, target)
        orig_opacity = target.opacity
        defer(setattr, target, "opacity", orig_opacity)

        # Moves and fades the target widget during swipe.
        offset = (touch.x - touch.ox) if is_horizontal else (touch.y - touch.oy)
        abs_ = abs
        async with (
            ak.move_on_when(touch.ud["kivyx_end"].wait()),
            ak.event_freq(Window, "on_touch_move", filter=lambda w, t, touch=touch: t is touch) as on_touch_move,
        ):
            with ak.transform(target, canvas_layer="outer") as ig:
                ig.add(translate := Translate())
                if is_horizontal:
                    while True:
                        await on_touch_move()
                        offset += touch.dx
                        translate.x = offset
                        target.opacity = (1.0 - abs_(offset) / delete_distance) * orig_opacity
                else:
                    while True:
                        await on_touch_move()
                        offset += touch.dy
                        translate.y = offset
                        target.opacity = (1.0 - abs_(offset) / delete_distance) * orig_opacity
        if abs_(offset) > delete_distance:
            on_delete_requested(target, touch)


def get_active_swipe2deletes() -> list[tuple[Widget, MotionEvent]]:
    '''
    Returns a list of (widget, touch) pairs for all ongoing swipe-to-delete gestures,
    where the ``widget`` is the widget being swiped and the ``touch`` is the
    :class:`~kivy.input.motionevent.MotionEvent` associated with the swipe.
    '''
    result = []
    for t in EventLoop.touches:
        try:
            ex_access = t.ud["kivyx_exclusive_access"]
        except KeyError:
            continue
        if (not ex_access.has_been_claimed) or t.ud["kivyx_abandon"].is_fired:
            continue
        match ex_access.params:
            case claimant, "swipe2delete":
                result.append((claimant, t))
    return result
