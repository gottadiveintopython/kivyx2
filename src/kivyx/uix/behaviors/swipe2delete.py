__all__ = (
    "enable_swipe2delete",
    "enable_swipe2delete_for_children",
    "KXSwipe2DeleteBehavior",
    "disable_and_remove",
    "ongoing_swipe2deletes",
)
from typing import Literal
from functools import partial
from collections.abc import Callable
from contextlib import AsyncExitStack

from kivy.metrics import dp
from kivy.properties import NumericProperty, BooleanProperty, OptionProperty, ObjectProperty
from kivy.clock import Clock
from kivy.base import EventLoop
from kivy.core.window import Window
from kivy.input.motionevent import MotionEvent
from kivy.uix.widget import Widget
from kivy.graphics import Translate
import asynckivy as ak

from kivyx.touch_filters import is_colliding_and_not_wheel
from kivyx.gesture_detectors import horizontal_swipe, vertical_swipe

class defaults:
    direction = "horizontal"
    swipe_distance = dp(20)
    delete_distance = dp(300)
    track_multiple_touches = False


def disable_and_remove(touch, widget):
    '''
    Default action performed when a swipe-to-delete gesture requests deletion.

    .. code-block::

        def disable_and_remove(touch, widget):
            widget.disabled = True
            widget.parent.remove_widget(widget)
    '''
    widget.disabled = True
    widget.parent.remove_widget(widget)


async def enable_swipe2delete_for_children(
    layout, /, *,
    touch_filter: Callable[[Widget, MotionEvent], bool]=is_colliding_and_not_wheel,
    direction: Literal["horizontal", "vertical"]=defaults.direction,
    swipe_distance=defaults.swipe_distance,
    delete_distance=defaults.delete_distance,
    on_delete_requested: Callable[[MotionEvent, Widget], None]=disable_and_remove,
    track_multiple_touches=defaults.track_multiple_touches,
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

    :param delete_distance:
        The minimum distance a recognized swipe gesture must travel to trigger ``on_delete_requested``
        when the touch is released.

    :param on_delete_requested:
        A callable invoked when a delete request is triggered. Defaults to :func:`disable_and_remove`.
        For its parameters, see :meth:`KXSwipe2DeleteBehavior.on_delete_requested`.

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
    direction: Literal["horizontal", "vertical"]=defaults.direction,
    swipe_distance=defaults.swipe_distance,
    delete_distance=defaults.delete_distance,
    on_delete_requested: Callable[[MotionEvent, Widget], None]=disable_and_remove,
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
    swipe_trigger,
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
            swipe_trigger(touch),
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
            on_delete_requested(touch, target)


class KXSwipe2DeleteBehavior:
    '''
    A mix-in class that adds swipe-to-delete functionality to a layout's children.

    (Some docstrings in this class are written in Japanese because the corresponding English
    documentation is already available in :func:`enable_swipe2delete_for_children`.)
    '''

    s2d_disabled = BooleanProperty(False)
    '''If either :attr:`~kivy.uix.widget.Widget.disabled` or :attr:`s2d_disabled` is True,
    the swipe-to-delete functionality is disabled. '''

    s2d_touch_filter = ObjectProperty(is_colliding_and_not_wheel)
    '''
    ``on_touch_down`` イベントがこの選別をくぐり抜けたタッチのみがスワイプとして認識され得る。
    既定値は :func:`~kivyx.touch_filters.is_colliding_and_not_wheel`。
    '''

    s2d_swipe_distance = NumericProperty(defaults.swipe_distance)
    '''タッチがスワイプとして認識されるために必要な移動量'''

    s2d_delete_distance = NumericProperty(defaults.delete_distance)
    '''指が離れた際に ``on_delete_requested`` イベントを引き起こすのに必要なスワイプの移動量'''

    s2d_direction = OptionProperty(defaults.direction, options=("horizontal", "vertical", ))
    '''スワイプの方向'''

    s2d_track_multiple_touches = BooleanProperty(defaults.track_multiple_touches)
    '''偽(既定値)の場合、１つタッチを監視している間に始まった他のタッチは無視される。'''

    def on_delete_requested(self, touch, child):
        '''
        :param touch: The :class:`~kivy.input.motionevent.MotionEvent` that triggered the
            ``on_delete_requested`` event, in window coordinates.
        :param child: The child widget for which deletion was requested.
        '''
        child.disabled = True
        self.remove_widget(child)

    def __init__(self, **kwargs):
        self.__main_task = ak.dummy_task
        self.register_event_type("on_delete_requested")
        super().__init__(**kwargs)
        t = Clock.schedule_once(self.__reset)
        self.bind(
            disabled=t,
            s2d_disabled=t,
            s2d_touch_filter=t,
            s2d_swipe_distance=t,
            s2d_delete_distance=t,
            s2d_direction=t,
            s2d_track_multiple_touches=t,
        )

    # Python's name mangling is weird. This method cannot be named '__reset'.
    def _KXSwipe2DeleteBehavior__reset(self, __):
        self.__main_task.cancel()
        if self.disabled or self.s2d_disabled:
            return
        self.__main_task = ak.managed_start(enable_swipe2delete_for_children(
            self,
            touch_filter=self.s2d_touch_filter,
            swipe_distance=self.s2d_swipe_distance,
            delete_distance=self.s2d_delete_distance,
            direction=self.s2d_direction,
            track_multiple_touches=self.s2d_track_multiple_touches,
            on_delete_requested=self.__dispatch_on_delete_requested_event,
        ))

    def __dispatch_on_delete_requested_event(self, touch, child):
        self.dispatch("on_delete_requested", touch, child)


def ongoing_swipe2deletes() -> list[tuple[Widget, MotionEvent]]:
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
