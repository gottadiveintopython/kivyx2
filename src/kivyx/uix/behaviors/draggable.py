__all__ = (
    "DragTarget", "KXDraggableBehavior", "KXDragTargetBehavior", "KXDragReorderBehavior",
    "ongoing_drags", "save_widget_state", "restore_widget_state",
)

import types
from typing import Union, TypeAlias
from inspect import isawaitable
from dataclasses import dataclass
from copy import deepcopy
from functools import partial

from kivy.properties import (
    BooleanProperty, ListProperty, StringProperty, NumericProperty, OptionProperty, AliasProperty,
    ObjectProperty,
)
from kivy.clock import Clock
from kivy.utils import rgba
from kivy.graphics import Color, Rectangle
from kivy.core.window import Window, WindowBase
from kivy.uix.widget import Widget
from kivy.uix.scrollview import ScrollView
import asynckivy as ak

from kivyx.touch_filters import is_opos_colliding_and_not_wheel

Wow: TypeAlias = Union[WindowBase, Widget]  # Window or Widget
DragTarget: TypeAlias = Union['KXDragTargetBehavior', 'KXDragReorderBehavior']


@dataclass(slots=True)
class DragContext:
    '''
    A dataclass that holds information about a drag.
    It is instantiated each time a drag occurs.
    '''

    draggable: "KXDraggableBehavior" = None
    '''
    (read-only) The widget that is being dragged.
    '''

    original_pos: tuple = None
    '''
    (read-only) The position of the draggable at the moment the drag starts.
    (in window coordinates).
    '''

    start_from: tuple = None
    '''
    (read-only) The position of the touch at the moment the drag starts.
    (in window coordinates).
    '''

    original_state: dict = None
    '''
    (read-only) The sizing and positioning state of the draggable at the moment the drag starts.
    This can be passed to :func:`restore_widget_state`.
    '''

    released_on: Union[None, DragTarget] = None
    '''
    (read-only) The widget where the draggable is released.
    '''


_shallow_copyable_property_names = (
    'x', 'y', 'width', 'height',
    'size_hint_x', 'size_hint_y',
    'size_hint_min_x', 'size_hint_min_y',
    'size_hint_max_x', 'size_hint_max_y',
)


def save_widget_state(widget, *, ignore_parent=False) -> dict:
    '''
    Copies and returns the values of sizing and positioning properties of a widget.

    .. code-blck::

        state = save_widget_state(widget)
    '''
    w = widget.__self__
    getattr_ = getattr
    state = {name: getattr_(w, name) for name in _shallow_copyable_property_names}
    state['pos_hint'] = deepcopy(w.pos_hint)
    if ignore_parent:
        return state
    parent = w.parent
    state['parent'] = parent
    if parent is not None:
        state['index'] = parent.children.index(w)
    return state


def restore_widget_state(widget, state: dict, *, ignore_parent=False):
    '''
    .. code-blck::

        state = save_widget_state(widget)
        ...
        restore_widget_state(widget, state)
    '''
    w = widget.__self__
    setattr_ = setattr
    for name in _shallow_copyable_property_names:
        setattr_(w, name, state[name])
    w.pos_hint = deepcopy(state['pos_hint'])
    if ignore_parent or 'parent' not in state:
        return
    if w.parent is not None:
        w.parent.remove_widget(w)
    parent = state['parent']
    if parent is None:
        return
    if parent is Window:
        parent.add_widget(w)  # 'Window.add_widget()' does not have a 'index' parameter
    else:
        parent.add_widget(w, index=state['index'])


def _create_spacer(**kwargs):
    color = kwargs.pop('color', None)
    spacer = Widget(**kwargs)
    with spacer.canvas:
        if color is None:
            Color(.2, .2, .2, .7)
        else:
            Color(*rgba(color))
        rect = Rectangle()
    ak.sync_attr((spacer, "pos"), (rect, "pos"))
    ak.sync_attr((spacer, "size"), (rect, "size"))
    return spacer


class KXDraggableBehavior:
    __events__ = (
        "on_drag_start", "on_drag_end", "on_drag_succeed", "on_drag_fail", "on_drag_cancel",
    )

    drag_cls = StringProperty()

    drag_distance = NumericProperty(ScrollView.scroll_distance.defaultvalue)

    drag_timeout = NumericProperty(0.2)
    '''in seconds. Defaults to 0.2.'''

    drag_enabled = BooleanProperty(True)
    '''Indicates whether this draggable can be dragged or not.
    Unlike the Kivy Garden's one, setting this to False cancels ongoing drag.
    '''

    drag_state = OptionProperty(None, options=('started', 'succeeded', 'failed', 'cancelled'), allownone=True)
    '''(read-only)'''

    is_being_dragged = AliasProperty(lambda self: self.drag_state is not None, bind=('drag_state', ), cache=True)
    '''(read-only)'''

    drag_touch_filter = ObjectProperty(is_opos_colliding_and_not_wheel)
    '''
    An ``on_touch_down`` event that does not pass this filter will immediately be disregarded
    as a dragging gesture.
    '''

    def drag_cancel(self):
        '''
        If the draggable is currently being dragged, cancels it.
        '''

    def drag_start(self, receiver: Wow, touch):
        '''
        Starts dragging if the draggable is not currently being dragged.

        :param receiver: The widget or Window that received the ``touch``.
        :param touch: The touch that is going to drag this draggable.

        Notes:

        * You are responsible for setting the size, position, or both of the draggable depending on the situation.
        '''

    def __init__(self, **kwargs):
        self.__main_task = ak.dummy_task
        self.__start_ev = ak.ExclusiveEvent()
        self.__cancel_ev = ak.ExclusiveEvent()
        self.drag_cancel = self.__cancel_ev.fire
        self.drag_start = self.__start_ev.fire
        super().__init__(**kwargs)
        t = Clock.schedule_once(self.__reset, -1)
        f = self.fbind
        f("disabled", t)
        f("drag_enabled", t)
        f("drag_touch_filter", t)

    # Python's name mangling is weird. This method cannot be named '__reset'.
    def _KXDraggableBehavior__reset(self, __):
        self.__main_task.cancel()
        if self.disabled or (not self.drag_enabled):
            return
        self.__main_task = ak.managed_start(ak.wait_all(
            self.__touch_down_listener(),
            self.__event_listener(),
        ))

    async def __touch_down_listener(self):
        on_touch_down = partial(ak.event, self, "on_touch_down", filter=self.drag_touch_filter)
        async with ak.open_nursery() as nursery:
            while True:
                __, touch = await on_touch_down()
                if self.is_being_dragged or touch.ud["kivyx_claim_signal"].is_fired:
                    continue
                if self.drag_timeout:
                    nursery.start(self._see_if_a_touch_actually_is_a_dragging_gesture(touch))
                else:
                    self.drag_start(self, touch)

    async def _see_if_a_touch_actually_is_a_dragging_gesture(self, touch, Window=Window, ak=ak):
        def is_same_touch(w, t, touch=touch):
            return t is touch
        async with (
            ak.move_on_when(touch.ud["kivyx_claim_signal"].wait()),
            ak.move_on_after(self.drag_timeout) as timeout_tracker,
            ak.event_freq(Window, "on_touch_move", filter=is_same_touch) as on_touch_move,
        ):
            abs_ = abs
            drag_distance = self.drag_distance
            ox, oy = self.to_window(*touch.opos)
            while True:
                await on_touch_move()
                dx = abs_(touch.x - ox)
                dy = abs_(touch.y - oy)
                if dy > drag_distance or dx > drag_distance:
                    break

        if timeout_tracker.finished:
            self.drag_start(Window, touch)

    async def __event_listener(self):
        cancel_ev_wait = self.__cancel_ev.wait
        start_ev_wait = self.__start_ev.wait
        perform_drag = self.__perform_drag
        while True:
            async with ak.move_on_when(cancel_ev_wait()):
                while True:
                    receiver, touch = (await start_ev_wait())[0]
                    await perform_drag(receiver, touch)

    async def __perform_drag(self, receiver: Wow, touch, Window=Window):
        '''
        :param receiver: The widget or Window that received the ``touch``.
        :param touch: The touch that is going to drag the draggable.
        '''
        def is_same_touch(w, t, touch=touch):
            return t is touch
        touch_ud = touch.ud
        try:
            ctx = DragContext(
                draggable=self,
                original_state=save_widget_state(self),
                original_pos=self.to_window(*self.pos),
                start_from=receiver.to_window(*touch.opos),
            )
            self_x, self_y = ctx.original_pos
            ox, oy = ctx.start_from
            offset_x = self_x - ox
            offset_y = self_y - oy

            # notify other widgets
            touch_ud['kivyx_drag_cls'] = self.drag_cls
            touch_ud['kivyx_drag_ctx'] = ctx
            touch_ud["kivyx_claim_signal"].fire()

            # move self under the Window
            if self.parent is not None:
                self.parent.remove_widget(self)
            self.size_hint_x = self.size_hint_y = None
            self.pos_hint = {}
            self.x = self_x
            self.y = self_y
            Window.add_widget(self)

            # actual dragging process
            self.dispatch('on_drag_start', touch, ctx)
            self.drag_state = 'started'
            async with(
                ak.move_on_when(touch_ud["kivyx_end_signal"].wait()),
                ak.event_freq(Window, "on_touch_move", filter=is_same_touch) as on_touch_move,
            ):
                while True:
                    await on_touch_move()
                    self.x = touch.x + offset_x
                    self.y = touch.y + offset_y

            # wait for other widgets to respond to the 'on_touch_up' event
            await ak.sleep(-1)

            ctx.released_on = released_on = touch_ud.get('kivyx_drag_released_on', None)
            if released_on is None or (not released_on.dispatch("on_drag_release", touch, ctx)):
                r = self.dispatch('on_drag_fail', touch, ctx)
                self.drag_state = 'failed'
            else:
                r = self.dispatch('on_drag_succeed', touch, ctx)
                self.drag_state = 'succeeded'
            if isawaitable(r):
                await r
        except ak.Cancelled:
            self.dispatch('on_drag_cancel', touch, ctx)
            self.drag_state = 'cancelled'
            raise
        finally:
            self.dispatch('on_drag_end', touch, ctx)
            self.drag_state = None
            touch_ud['kivyx_drag_released_on'] = None
            del touch_ud['kivyx_drag_cls']
            del touch_ud['kivyx_drag_ctx']

    def on_drag_start(self, touch, ctx: DragContext):
        pass

    def on_drag_end(self, touch, ctx: DragContext):
        pass

    def on_drag_succeed(self, touch, ctx: DragContext):
        pass

    async def on_drag_fail(self, touch, ctx: DragContext):
        x, y = ctx.original_pos
        await ak.anim_attrs(self, duration=.1, x=x, y=y)
        restore_widget_state(self, ctx.original_state)

    def on_drag_cancel(self, touch, ctx: DragContext):
        restore_widget_state(self, ctx.original_state)


def ongoing_drags() -> list[KXDraggableBehavior]:
    '''Returns a list of draggables currently being dragged'''
    return [c for c in Window.children if getattr(c, 'is_being_dragged', False)]


class KXDragTargetBehavior:
    __events__ = ("on_drag_release", "on_drag_enter", "on_drag_leave", )
    drag_classes = ListProperty([])

    def __init__(self, **kwargs):
        self.__main_task = ak.dummy_task
        super().__init__(**kwargs)
        self.__ud_key = "KXDragTargetBehavior." + str(self.uid)
        t = Clock.schedule_once(self.__reset, -1)
        f = self.fbind
        f("disabled", t)
        f("drag_classes", t)

    # Python's name mangling is weird. This method cannot be named '__reset'.
    def _KXDragTargetBehavior__reset(self, __):
        self.__main_task.cancel()
        if self.disabled:
            return
        self.__main_task = ak.managed_start(self.__main())

    @staticmethod
    def __untracked_touch_filter(ud_key, collide_point, widget, touch) -> bool:
        return (ud_key not in touch.ud) and collide_point(*touch.pos)

    async def __main(self):
        on_touch_move = partial(ak.event, self, "on_touch_move", filter=partial(
            self.__untracked_touch_filter, self.__ud_key, self.collide_point))
        async with ak.open_nursery() as nursery:
            while True:
                __, touch = await on_touch_move()
                touch.ud[self.__ud_key] = None
                if touch.ud.get("kivyx_drag_cls", None) in self.drag_classes:
                    nursery.start(self.__touch_handler(touch))

    async def __touch_handler(self, touch):
        ctx = touch.ud['kivyx_drag_ctx']
        dispatch = self.dispatch
        try:
            inside = True
            async with ak.move_on_when(ak.event(ctx.draggable, "on_drag_cancel")):
                dispatch('on_drag_enter', touch, ctx)
                async with (
                    ak.move_on_when(touch.ud["kivyx_end_signal"].wait()),
                    _touch_move_events(self, touch) as on_touch_move,
                ):
                    while True:
                        if inside is await on_touch_move():
                            continue
                        inside = not inside
                        dispatch('on_drag_enter' if inside else "on_drag_leave", touch, ctx)
                if inside:
                    touch.ud.setdefault('kivyx_drag_released_on', self)
        finally:
            if inside:
                dispatch("on_drag_leave", touch, ctx)

    def on_drag_enter(self, touch, ctx: DragContext) -> bool:
        pass

    on_drag_leave = on_drag_enter

    def on_drag_release(self, touch, ctx: DragContext) -> bool:
        d = ctx.draggable
        d.parent.remove_widget(d)
        os = ctx.original_state
        d.size_hint_x = os['size_hint_x']
        d.size_hint_y = os['size_hint_y']
        d.pos_hint = os['pos_hint']
        self.add_widget(d)
        return True


class KXDragReorderBehavior:
    __events__ = ("on_drag_release", )
    drag_classes = ListProperty([])

    spacer_widgets = ListProperty(None)
    '''
    A list of spacer widgets.
    The number of these will be the maximum number of simultaneous drags the :class:`KXDragReorderBehavior`` can handle.
    '''

    def __init__(self, **kwargs):
        self.__main_task = ak.dummy_task
        super().__init__(**kwargs)
        self.__ud_key = "KXDragReorderBehavior." + str(self.uid)
        t = Clock.schedule_once(self.__reset, -1)
        f = self.fbind
        f("disabled", t)
        f("drag_classes", t)
        f("spacer_widgets", t)

    # Python's name mangling is weird. This method cannot be named '__reset'.
    def _KXDragReorderBehavior__reset(self, __):
        self.__main_task.cancel()
        if self.disabled:
            return
        s = self.spacer_widgets
        self.__inactive_spacers = [_create_spacer(size_hint_min=("50dp", "50dp")), ] \
            if s is None else s.copy()
        self.__main_task = ak.managed_start(ak.wait_all(
            self.__listen_to_touch_down_events(),
            self.__listen_to_touch_move_events(),
        ))

    @staticmethod
    def __touch_move_filter(ud_key, inactive_spacers, collide_point, widget, touch):
        return (ud_key not in touch.ud) and inactive_spacers and collide_point(*touch.pos)

    async def __listen_to_touch_move_events(self):
        ud_key = self.__ud_key
        drag_classes = self.drag_classes
        handler = self.__place_a_spacer_under_drag
        on_touch_move = partial(ak.event, self, "on_touch_move", filter=partial(
            self.__touch_move_filter, ud_key, self.__inactive_spacers, self.collide_point))
        async with ak.open_nursery() as nursery:
            while True:
                __, touch = await on_touch_move()
                touch.ud[ud_key] = None
                if touch.ud.get("kivyx_drag_cls", None) in drag_classes:
                    nursery.start(handler(touch))

    async def __listen_to_touch_down_events(self):
        handler = self.__handle_a_potential_dragging_gesture
        on_touch_down = partial(ak.event, self, "on_touch_down", filter=is_opos_colliding_and_not_wheel)
        async with ak.open_nursery() as nursery:
            while True:
                __, touch = await on_touch_down()
                nursery.start(handler(touch))

    async def __handle_a_potential_dragging_gesture(self, touch):
        ud = touch.ud
        ud[self.__ud_key] = None
        await ud["kivyx_claim_signal"].wait()
        if ud.get("kivyx_drag_cls", None) not in self.drag_classes:
            return
        ox, oy = self.parent.to_widget(*ud['kivyx_drag_ctx'].start_from)
        if self.__inactive_spacers and self.collide_point(ox, oy):
            __, idx = self.get_child_under_drag(*self.to_local(ox, oy))
            await self.__place_a_spacer_under_drag(touch, idx or 0)
        else:
            del ud[self.__ud_key]

    async def __place_a_spacer_under_drag(self, touch, spacer_initial_index=0):
        spacer = self.__inactive_spacers.pop()
        touch_ud = touch.ud
        get_child_under_drag = self.get_child_under_drag
        remove_widget = self.remove_widget
        add_widget = self.add_widget
        to_local = self.to_local
        ctx = touch_ud['kivyx_drag_ctx']
        try:
            restore_widget_state(spacer, ctx.original_state, ignore_parent=True)
            add_widget(spacer, index=spacer_initial_index)
            async with ak.move_on_when(ak.event(ctx.draggable, "on_drag_cancel")):
                async with (
                    ak.move_on_when(touch_ud["kivyx_end_signal"].wait()),
                    _touch_move_events(self, touch) as on_touch_move,
                ):
                    while True:
                        if not await on_touch_move():
                            return
                        child, idx = get_child_under_drag(*to_local(*touch.pos))
                        if child is spacer:
                            continue
                        if child is None:
                            if self.children:
                                continue
                            else:
                                idx = 0
                        remove_widget(spacer)
                        add_widget(spacer, index=idx)
                if 'kivyx_drag_released_on' not in touch_ud:
                    touch_ud['kivyx_drag_released_on'] = self
                    touch_ud['kivyx_draggable_index'] = self.children.index(spacer)
        finally:
            del touch_ud[self.__ud_key]
            self.remove_widget(spacer)
            self.__inactive_spacers.append(spacer)


    def on_drag_release(self, touch, ctx: DragContext) -> bool:
        d = ctx.draggable
        d.parent.remove_widget(d)
        os = ctx.original_state
        d.size_hint_x = os['size_hint_x']
        d.size_hint_y = os['size_hint_y']
        d.pos_hint = os['pos_hint']
        self.add_widget(d, index=touch.ud["kivyx_draggable_index"])
        return True

    def get_child_under_drag(self, x, y) -> tuple[Widget, int]:
        """Returns a tuple of the widget in children that is under the
        given position and its index. Returns (None, None) if there is no
        widget under that position.
        """
        for index, widget in enumerate(self.children):
            if widget.collide_point(x, y):
                return (widget, index)
        return (None, None)


class _touch_move_events:
    '''
    DragTargetが一部しか見えていない状況(例えばScrollView内に置かれているとか)を考えると、
    通常のタッチイベントも受け取って 見えている範囲でドラッグ操作が行われているかを判別しないといけない為、
    独自のタッチ処理が要る。

    .. code-block::

        async with(
            move_on_when(touch.ud["kivyx_end_signal"].wait()),
            _touch_move_events(widget, touch) as on_touch_move,
        ):
            while True:
                inside = await on_touch_move()
                ...
    '''

    def __init__(self, widget, touch):
        self.widget = widget
        self.touch = touch

    @staticmethod
    @types.coroutine
    def _wait_one(_f=ak._sleep_forever):
        return (yield _f)[0][0]

    @staticmethod
    def _on_touch_move(task_step, collide_point, cancel_resumption, touch, w, t) -> bool:
        if touch is t and collide_point(*t.pos):
            cancel_resumption()
            task_step(True)

    @staticmethod
    def _on_touch_move_win(trigger_resumption, touch, w, t) -> bool:
        if touch is t:
            trigger_resumption()

    @types.coroutine
    def __aenter__(self, partial=partial):
        widget = self.widget
        touch = self.touch
        task = (yield ak._current_task)[0][0]
        self.trigger_resumption = t = Clock.create_trigger(partial(task._step, False), -1)
        self._uid_win = Window.fbind("on_touch_move", partial(self._on_touch_move_win, t, touch))
        self._uid = widget.fbind("on_touch_move",
            partial(self._on_touch_move, task._step, widget.collide_point, t.cancel, touch))
        return self._wait_one

    async def __aexit__(self, *__):
        Window.unbind_uid("on_touch_move", self._uid_win)
        self.widget.unbind_uid("on_touch_move", self._uid)
        self.trigger_resumption.cancel()
