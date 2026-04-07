from typing import TypeAlias, Literal, Any
from collections.abc import Sequence, Callable
from functools import partial
from contextlib import ExitStack, nullcontext

from kivy.properties import BooleanProperty, ListProperty, ObjectProperty
from kivy.graphics import PushMatrix, PopMatrix, Translate, InstructionGroup
from kivy.base import EventLoop
from kivy.clock import Clock
from kivy.input.motionevent import MotionEvent
from kivy.core.window import Window
from kivy.uix.widget import Widget
import asynckivy as ak

from kivyx.touch_filters import is_colliding_and_not_wheel
from kivyx.gesture_detectors import GestureDetector, long_press
from ._common import DragCls, noop

DragResult: TypeAlias = Literal["succeeded", "failed", "cancelled"]
OnDragStart: TypeAlias = Callable[[Widget, MotionEvent, DragCls], Any]
OnDragEnd: TypeAlias = Callable[[Widget, MotionEvent, DragCls, DragResult], Any]


async def perform_drag(widget, touch, *, drag_cls=None, include_pre_drag_distance=True):
    '''
    Drags the widget with the given touch until it is released.

    .. code-block::

        success = await perform_drag(widget, touch)

    :return:
        Whether the dragged widget was accepted by a drop target.

    :param widget:
        The widget being dragged.

    :param touch:
        The touch to drag with. Exclusive access to this touch must not have been claimed.

    :param include_pre_drag_distance:
        Whether to apply the distance already traveled by the touch since its
        ``on_touch_down`` event to the initial offset of the drag.
    '''
    if include_pre_drag_distance:
        initial_offset = widget.to_window(touch.x - touch.ox, touch.y - touch.oy)
    else:
        initial_offset = widget.to_window(0, 0)
    parent = widget.parent
    if parent is None:
        restore_original_placement = noop
    else:
        restore_original_placement = partial(parent.add_widget, widget, index=parent.children.index(widget))

    drop_handlers = []
    touch.ud["kivyx_exclusive_access"].claim(widget, "drag_n_drop", drag_cls, drop_handlers)
    if parent is not None:
        parent.remove_widget(widget)

    async with ak.move_on_when(touch.ud["kivyx_abandon"].wait()):
        accepted = False
        try:
            with ExitStack() as stack:
                defer = stack.callback

                overlay = InstructionGroup()
                defer(overlay.clear)
                add = overlay.add
                add(PushMatrix())
                add(translation := Translate(*initial_offset))
                add(widget.canvas)
                add(PopMatrix())

                Window.canvas.add(overlay)
                defer(Window.canvas.remove, overlay)

                async with (
                    ak.move_on_when(touch.ud["kivyx_end"].wait()),
                    ak.event_freq(Window, "on_touch_move", filter=lambda w, t, touch=touch: t is touch) as on_touch_move,
                ):
                    offset_x, offset_y = initial_offset
                    while True:
                        await on_touch_move()
                        offset_x += touch.dx
                        offset_y += touch.dy
                        translation.xy = (offset_x, offset_y)

                # Wait for other widgets to respond to the `on_touch_up` event.
                # This populates the `drop_handlers` list with handlers from widgets that declared to accept the drop.
                await ak.sleep(-1)

                overlay.remove(widget.canvas)
                for f in drop_handlers:
                    if f():
                        accepted = True
                        break
                if not accepted:
                    # No one accepted the drop, but we cannot call `restore_original_placement`
                    # yet because `widget.canvas` is still in `Window.canvas``.
                    overlay.insert(2, widget.canvas)
                    await ak.anim_attrs(translation, duration=.1, xy=initial_offset)
        finally:
            if not accepted:
                restore_original_placement()

        return accepted


async def _watch_for_drag_start(
    target: Widget, touch, *,
    drag_cls,
    triggers: Sequence[GestureDetector],
    on_start: OnDragStart,
    on_end: OnDragEnd,
    _active_targets=[],
):
    '''
    Monitors ``touch`` and starts dragging ``target`` when any of the ``triggers`` fires.
    '''
    ud = touch.ud
    async with ak.move_on_when(ud["kivyx_abandon"].wait()):
        tasks = await ak.wait_any(
            ud["kivyx_end"].wait(),
            ud["kivyx_exclusive_access"].wait_for_one_to_claim(),
            *[trigger(touch) for trigger in triggers],
        )
        if any([t.finished for t in tasks[:2]]) or all([t.cancelled for t in tasks]) or target in _active_targets:
            return
        on_start(target, touch, drag_cls)
        result = "cancelled"
        _active_targets.append(target)
        try:
            if await perform_drag(target, touch, drag_cls=drag_cls):
                result = "succeeded"
            else:
                result = "failed"
        finally:
            _active_targets.remove(target)
            on_end(target, touch, drag_cls, result)


async def enable_drag(
    widget, *,
    drag_cls=None,
    touch_filter: Callable[[Widget, MotionEvent], bool]=is_colliding_and_not_wheel,
    consume_touch: bool=False,
    triggers: Sequence[GestureDetector]=(long_press, ),
    on_start: OnDragStart=noop,
    on_end: OnDragEnd=noop,
):
    '''
    Makes ``widget`` draggable until the returned coroutine is cancelled.

    See :func:`enable_drag_for_children` for the parameters.
    '''
    widget = widget.__self__
    on_touch_down = partial(ak.event, widget, "on_touch_down", filter=touch_filter, stop_dispatching=consume_touch)
    watch_for_drag_start = partial(
        _watch_for_drag_start, drag_cls=drag_cls, triggers=triggers, on_start=on_start, on_end=on_end)

    with ak.suppress_event(widget, "on_touch_down", filter=touch_filter) if consume_touch else nullcontext():
        while True:
            __, touch = await on_touch_down()
            await watch_for_drag_start(widget, touch)


async def enable_drag_for_children(
    layout, *,
    drag_cls=None,
    touch_filter: Callable[[Widget, MotionEvent], bool]=is_colliding_and_not_wheel,
    consume_touch: bool=False,
    triggers: Sequence[GestureDetector]=(long_press, ),
    track_multiple_touches: bool=False,
    on_start: OnDragStart=noop,
    on_end: OnDragEnd=noop,
):
    '''
    Makes ``layout``'s children draggable until the returned coroutine is cancelled.

    :param touch_filter:
        Any touch whose ``on_touch_down`` event does not pass this filter is ignored.
        Defaults to :func:`~kivyx.touch_filters.is_colliding_and_not_wheel`.

    :param consume_touch:
        Whether to consume ``on_touch_down`` events that pass ``touch_filter``.

    :param triggers:
        Drag starts when any of these gestures is detected.

    :param track_multiple_touches:
        Whether to track multiple touches simultaneously (multi-touch). If False (the default),
        once a touch starts being tracked, subsequent touches are ignored until the tracked touch
        ends or exclusive access to it is claimed by someone else.
    '''
    from kivyx.utils import find_child_at

    layout = layout.__self__
    children = layout.children
    to_local = layout.to_local
    on_touch_down = partial(ak.event, layout, "on_touch_down", filter=touch_filter, stop_dispatching=consume_touch)
    watch_for_drag_start = partial(
        _watch_for_drag_start, drag_cls=drag_cls, triggers=triggers, on_start=on_start, on_end=on_end)

    with ak.suppress_event(layout, "on_touch_down", filter=touch_filter) if consume_touch else nullcontext():
        if track_multiple_touches:
            async with ak.open_nursery() as nursery:
                while True:
                    __, touch = await on_touch_down()
                    child = find_child_at(children, *to_local(*touch.pos))
                    if child is not None:
                        nursery.start(watch_for_drag_start(child, touch))
        else:
            while True:
                __, touch = await on_touch_down()
                child = find_child_at(children, *to_local(*touch.pos))
                if child is not None:
                    await watch_for_drag_start(child, touch)


def get_active_drags() -> list[tuple[Widget, MotionEvent, DragCls]]:
    '''
    Returns a list of ``(dragged_widget, touch, drag_cls)`` tuples for all active drags.
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
            case dragged_widget, "drag_n_drop", drag_cls, _:
                result.append((dragged_widget, t, drag_cls))
    return result


class KXDraggableBehavior:
    '''
    Mixin class that adds draggable behavior to widgets.
    '''

    drag_disabled = BooleanProperty(False)
    '''If either :attr:`~kivy.uix.widget.Widget.disabled` or :attr:`drag_disabled` is True,
    dragging is disabled.'''

    drag_touch_filter = ObjectProperty(is_colliding_and_not_wheel)
    '''
    Any touch whose ``on_touch_down`` event does not pass this filter is ignored.
    Defaults to :func:`~kivyx.touch_filters.is_colliding_and_not_wheel`.
    '''

    drag_is_in_progress = BooleanProperty(False)
    '''(read-only) Whether a drag is currently in progress on this widget.'''

    drag_cls = ObjectProperty(None, allownone=True)
    '''The drag class associated with this widget.'''

    drag_triggers = ListProperty([long_press])
    '''Drag starts when any of these gestures is detected.'''

    def drag_cancel(self):
        '''Cancels the ongoing drag on this widget, if any.'''

    def on_drag_start(self, touch, drag_cls):
        '''
        :param touch:
            The :class:`~kivy.input.motionevent.MotionEvent` that triggered the drag.
            It is usually in window coordinates, but that depends on :attr:`drag_triggers`.
        '''
        self.drag_cancel = touch.ud["kivyx_abandon"].fire
        self.drag_is_in_progress = True

    def on_drag_end(self, touch, drag_cls, result: DragResult):
        '''
        :param touch:
            The :class:`~kivy.input.motionevent.MotionEvent` that triggered the drag,
            in window coordinates.
        '''
        self.drag_is_in_progress = False

    def __init__(self, **kwargs):
        self.__main_task = ak.dummy_task
        self.register_event_type("on_drag_start")
        self.register_event_type("on_drag_end")
        super().__init__(**kwargs)
        t = Clock.schedule_once(self.__reset, -1)
        self.bind(
            disabled=t,
            drag_disabled=t,
            drag_touch_filter=t,
            drag_cls=t,
            drag_triggers=t,
        )

    # Python's name mangling is weird. This method cannot be named '__reset'.
    def _KXDraggableBehavior__reset(self, __):
        self.__main_task.cancel()
        if self.disabled or self.drag_disabled:
            return
        self.__main_task = ak.managed_start(enable_drag(
            self,
            touch_filter=self.drag_touch_filter,
            drag_cls=self.drag_cls,
            triggers=self.drag_triggers,
            consume_touch=False,
            on_start=self.__dispatch_on_drag_start_event,
            on_end=self.__dispatch_on_drag_end_event,
        ))

    @staticmethod
    def __dispatch_on_drag_start_event(self, touch, drag_cls):
        self.dispatch("on_drag_start", touch, drag_cls)

    @staticmethod
    def __dispatch_on_drag_end_event(self, touch, drag_cls, result):
        self.dispatch("on_drag_end", touch, drag_cls, result)
