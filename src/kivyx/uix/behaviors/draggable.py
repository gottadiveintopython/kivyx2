__all__ = (
    "DragTarget", "KXDraggableBehavior", "KXDragTargetBehavior", "KXDragReorderBehavior",
    "ongoing_drags", "save_widget_state", "restore_widget_state",
)

from typing import List, Tuple, Union
from inspect import isawaitable
from dataclasses import dataclass
from copy import deepcopy

from kivy.properties import (
    BooleanProperty, ListProperty, StringProperty, NumericProperty, OptionProperty, AliasProperty,
)
from kivy.clock import Clock
from kivy.factory import Factory
from kivy.core.window import Window
from kivy.uix.widget import Widget
from kivy.uix.scrollview import ScrollView
import asynckivy as ak

from kivyx.touch_filters import is_opos_colliding, is_opos_colliding_and_not_wheel, is_colliding


Wow = Union[Window, Widget]  # Window or Widget


@dataclass
class DragContext:
    original_pos_win: tuple = None
    '''(read-only) The position of the draggable at the time the drag has
    started. (in window coordinates).
    '''

    original_state: dict = None
    '''
    (read-only) The state of the draggable at the time the drag has started.
    This can be passed to ``restore_widget_state()``.
    '''

    acceptor: Union[None, 'KXDragTargetBehavior', 'KXDragReorderBehavior'] = None
    '''(read-only) The widget that accepted the drag.
    This will be set only when an ``on_drag_succeed`` occurs.
    '''

    denier: Union[None, 'KXDragTargetBehavior', 'KXDragReorderBehavior'] = None
    '''(read-only) The widget that denied the drag.
    This will be set only when an ``on_drag_fail`` occurs.
    '''


_shallow_copyable_property_names = (
    'x', 'y', 'width', 'height',
    'size_hint_x', 'size_hint_y',
    'size_hint_min_x', 'size_hint_min_y',
    'size_hint_max_x', 'size_hint_max_y',
)


def save_widget_state(widget, *, ignore_parent=False) -> dict:
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
    '''(internal)'''
    from kivy.uix.widget import Widget
    from kivy.utils import rgba
    from kivy.graphics import Color, Rectangle
    spacer = Widget(size_hint_min=('50dp', '50dp'))
    with spacer.canvas:
        color = kwargs.get('color', None)
        if color is None:
            Color(.2, .2, .2, .7)
        else:
            Color(*rgba(color))
        rect_inst = Rectangle(size=spacer.size)
    spacer.bind(
        pos=lambda __, value: setattr(rect_inst, 'pos', value),
        size=lambda __, value: setattr(rect_inst, 'size', value),
    )
    return spacer


class KXDraggableBehavior:
    __events__ = (
        "on_drag_start", "on_drag_end", "on_drag_succeed", "on_drag_fail", "on_drag_cancel",
    )

    drag_cls = StringProperty()

    drag_distance = NumericProperty(ScrollView.scroll_distance.defaultvalue)

    drag_timeout = NumericProperty(ScrollView.scroll_timeout.defaultvalue)
    '''in seconds. Defaults to 0.2.'''

    drag_enabled = BooleanProperty(True)
    '''Indicates whether this draggable can be dragged or not. Changing this
    doesn't affect ongoing drag. Call :meth:`drag_cancel` if you want to do that.
    '''

    drag_state = OptionProperty(None, options=('started', 'succeeded', 'failed', 'cancelled'), allownone=True)
    '''(read-only)'''

    is_being_dragged = AliasProperty(lambda self: self.drag_state is not None, bind=('drag_state', ), cache=True)
    '''(read-only)'''

    def drag_cancel(self):
        '''
        If the draggable is currently being dragged, cancels it.
        '''
        self.__main_task.cancel()

    def __init__(self, **kwargs):
        self.__main_task = ak.dummy_task
        super().__init__(**kwargs)
        self.bind(
            on_touch_down=is_opos_colliding,
            on_touch_move=is_colliding,
            on_touch_up=is_colliding,
        )
        self.fbind("on_touch_down", self.__on_touch_down)

    def _is_a_touch_potentially_a_dragging_gesture(self, touch) -> bool:
        '''
        ``on_touch_down`` event that does not pass this filter will immediately be disregarded
        as a dragging gesture.
        '''
        return self.collide_point(*touch.opos) and (not touch.is_mouse_scrolling)

    @property
    def __can_perform_drag(self) -> bool:
        return self.drag_enabled and (not self.is_being_dragged)

    def __on_touch_down(self, touch):
        if self._is_a_touch_potentially_a_dragging_gesture(touch) and self.__can_perform_drag:
            if self.drag_timeout:
                ak.managed_start(self._see_if_a_touch_actually_is_a_dragging_gesture(touch))
            else:
                ak.managed_start(self._perform_drag(touch))

    async def _see_if_a_touch_actually_is_a_dragging_gesture(self, touch, Window=Window):
        async with ak.move_on_after(self.drag_timeout) as timeout_tracker:
            # LOAD_FAST
            abs_ = abs
            drag_distance = self.drag_distance
            ox, oy = self.to_window(*touch.opos)

            async with(
                ak.move_on_when(touch.ud["kivyx_claim_signal"].wait()),
                ak.move_on_when(ak.event(Window, "on_touch_up")),
                ak.event_freq(Window, "on_touch_move") as on_touch_move,
            ):
                while True:
                    await on_touch_move()
                    dx = abs_(touch.x - ox)
                    dy = abs_(touch.y - oy)
                    if dy > drag_distance or dx > drag_distance:
                        break

        if timeout_tracker.finished and self.__can_perform_drag:
            ak.managed_start(self._perform_drag(touch, Window))

    def start_dragging_from_others_touch(self, receiver: Wow, touch):
        '''
        You are responsible for setting the size, position, or both of the draggable before calling this method.
 
        :param receiver: The widget or Window that received the ``touch``.
        :param touch: The touch that is going to drag the draggable.
        '''
        if self.__can_perform_drag:
            ak.managed_start(self._perform_drag(touch, receiver))
        else:
            raise Exception("Draggable is unable to start a drag operation right now.")

    async def _perform_drag(self, touch, receiver: Wow, Window=Window):
        touch_ud = touch.ud
        touch_ud["kivyx_claim_signal"].fire()
        try:
            original_pos_win = self.to_window(*self.pos)
            ox, oy = receiver.to_window(*touch.opos)
            self_x, self_y = self.to_window(*self.pos)
            offset_x = self_x - ox
            offset_y = self_y - oy
            ctx = DragContext(
                original_pos_win=original_pos_win,
                original_state=save_widget_state(self),
            )

            # move self under the Window
            if self.parent is not None:
                self.parent.remove_widget(self)
            self.size_hint = (None, None, )
            self.pos_hint = {}
            self.pos = (
                original_pos_win[0] - offset_x,
                original_pos_win[1] - offset_y,
            )
            Window.add_widget(self)

            # mark the touch so that other widgets can react to this drag
            touch_ud['kivyx_drag_cls'] = self.drag_cls
            touch_ud['kivyx_draggable'] = self
            touch_ud['kivyx_drag_ctx'] = ctx

            # store the task instance so that the user can cancel it later
            self.__main_task.cancel()
            self.__main_task = await ak.current_task()

            # actual dragging process
            self.dispatch('on_drag_start', touch, ctx)
            self.drag_state = 'started'
            async with(
                ak.move_on_when(ak.event(Window, "on_touch_up")),
                ak.event_freq(Window, "on_touch_move") as on_touch_move,
            ):
                while True:
                    await on_touch_move()
                    self.x = touch.x + offset_x
                    self.y = touch.y + offset_y

            # wait for other widgets to react to 'on_touch_up'
            await ak.sleep(-1)

            acceptor = touch_ud.get('kivyx_potential_drag_acceptor', None)
            if acceptor is None or (not acceptor.accept_drag(touch, ctx, self)):
                ctx.denier = acceptor
                r = self.dispatch('on_drag_fail', touch, ctx)
                self.drag_state = 'failed'
            else:
                ctx.acceptor = acceptor
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
            touch_ud['kivyx_potential_drag_acceptor'] = None
            del touch_ud['kivyx_drag_cls']
            del touch_ud['kivyx_draggable']
            del touch_ud['kivyx_drag_ctx']

    def on_drag_start(self, touch, ctx: DragContext):
        pass

    def on_drag_end(self, touch, ctx: DragContext):
        pass

    def on_drag_succeed(self, touch, ctx: DragContext):
        pass

    async def on_drag_fail(self, touch, ctx: DragContext):
        x, y = ctx.original_pos_win
        await ak.anim_attrs(self, duration=.1, x=x, y=y)
        restore_widget_state(self, ctx.original_state)

    def on_drag_cancel(self, touch, ctx: DragContext):
        restore_widget_state(self, ctx.original_state)


def ongoing_drags() -> List[KXDraggableBehavior]:
    '''Returns a list of draggables currently being dragged'''
    return [c for c in Window.children if getattr(c, 'is_being_dragged', False)]


class KXDragTargetBehavior:
    drag_classes = ListProperty([])
    '''Same as drag_n_drop's '''

    def on_touch_up(self, touch):
        r = super().on_touch_up(touch)
        touch_ud = touch.ud
        if touch_ud.get('kivyx_drag_cls', None) in self.drag_classes:
            if self.collide_point(*touch.pos):
                touch_ud.setdefault('kivyx_potential_drag_acceptor', self)
        return r

    def accept_drag(self, touch, ctx: DragContext, draggable: KXDraggableBehavior) -> bool:
        d = draggable
        d.parent.remove_widget(d)
        os = ctx.original_state
        d.size_hint_x = os['size_hint_x']
        d.size_hint_y = os['size_hint_y']
        d.pos_hint = os['pos_hint']
        self.add_widget(d)
        return True


class KXDragReorderBehavior:
    drag_classes = ListProperty([])
    '''Same as drag_n_drop's '''

    spacer_widgets = ListProperty([])
    '''A list of spacer widgets. The number of them will be the
    maximum number of simultaneous drags ``KXDragReorderBehavior`` can handle.

    This property can be changed only when there is no ongoing drag in this widget.
    '''

    def __init__(self, **kwargs):
        self._active_spacers = []
        self._inactive_spacers = None
        Clock.schedule_once(self._init_spacers)
        super().__init__(**kwargs)
        self.__ud_key = 'KXDragReorderBehavior.' + str(self.uid)

    def accept_drag(self, touch, ctx: DragContext, draggable: KXDraggableBehavior) -> bool:
        '''Determines whether the reorderable is willing to accept the drag'''
        return True

    def _init_spacers(self, dt):
        if self._inactive_spacers is None:
            self.spacer_widgets.append(_create_spacer())

    def on_spacer_widgets(self, __, spacer_widgets):
        if self._active_spacers:
            raise Exception("Do not change the 'spacer_widgets' when there is an ongoing drag.")
        self._inactive_spacers = [w.__self__ for w in spacer_widgets]

    def get_widget_under_drag(self, x, y) -> Tuple[Widget, int]:
        """Returns a tuple of the widget in children that is under the
        given position and its index. Returns (None, None) if there is no
        widget under that position.
        """
        x, y = self.to_local(x, y)
        for index, widget in enumerate(self.children):
            if widget.collide_point(x, y):
                return (widget, index)
        return (None, None)

    def on_touch_move(self, touch):
        ud_key = self.__ud_key
        touch_ud = touch.ud
        if ud_key not in touch_ud and self._inactive_spacers and self.collide_point(*touch.pos):
            drag_cls = touch_ud.get('kivyx_drag_cls', None)
            if drag_cls is not None:
                touch_ud[ud_key] = None
                if drag_cls in self.drag_classes:
                    ak.managed_start(ak.wait_any(
                        self._place_a_spacer_widget_under_the_drag(touch),
                        ak.event(touch.ud['kivyx_draggable'], 'on_drag_end'),
                    ))
        return super().on_touch_move(touch)

    async def _place_a_spacer_widget_under_the_drag(self, touch):
        spacer = self._inactive_spacers.pop()
        self._active_spacers.append(spacer)

        # LOAD_FAST
        collide_point = self.collide_point
        get_widget_under_drag = self.get_widget_under_drag
        remove_widget = self.remove_widget
        add_widget = self.add_widget
        touch_ud = touch.ud

        try:
            restore_widget_state(
                spacer,
                touch_ud['kivyx_drag_ctx'].original_state,
                ignore_parent=True)
            add_widget(spacer)
            async for __ in ak.rest_of_touch_events(self, touch):
                x, y = touch.pos
                if collide_point(x, y):
                    widget, idx = get_widget_under_drag(x, y)
                    if widget is spacer:
                        continue
                    if widget is None:
                        if self.children:
                            continue
                        else:
                            idx = 0
                    remove_widget(spacer)
                    add_widget(spacer, index=idx)
                else:
                    del touch_ud[self.__ud_key]
                    return
            if 'kivyx_potential_drag_acceptor' not in touch_ud:
                touch_ud['kivyx_potential_drag_acceptor'] = self
                touch_ud['kivyx_droppable_index'] = self.children.index(spacer)
        finally:
            self.remove_widget(spacer)
            self._inactive_spacers.append(spacer)
            self._active_spacers.remove(spacer)
