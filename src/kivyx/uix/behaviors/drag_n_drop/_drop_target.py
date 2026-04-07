from functools import partial

from kivy.clock import Clock
from kivy.properties import BooleanProperty, ObjectProperty
import asynckivy as ak

from kivyx.utils import visibility_aware_touch_movements
from ._common import noop, ACCEPT_ANY, DragClasses


def _add_widget_and_return_true(drop_target, touch, drag_cls, dragged_widget):
    drop_target.add_widget(dragged_widget)
    return True


async def enable_drop_target(widget, *, drag_classes: DragClasses=ACCEPT_ANY,
                             on_enter=noop, on_leave=noop, on_drop=_add_widget_and_return_true):
    '''
    Enables ``widget`` to act as a drop target until the returned coroutine is cancelled.

    :param drag_classes:
        Drag classes accepted by this drop target.

    :param on_enter:
        Called when a dragged widget enters the drop target.
        See :meth:`KXDropTargetBehavior.on_drag_enter` for details.

    :param on_leave:
        Called when a dragged widget leaves the drop target.
        See :meth:`KXDropTargetBehavior.on_drag_leave` for details.

    :param on_drop:
        Called when a dragged widget is dropped on the drop target.
        See :meth:`KXDropTargetBehavior.on_drop` for details.
    '''
    widget = widget.__self__

    async with ak.open_nursery() as nursery:
        def on_touch_xxx(
            widget, touch,
            seen="kivyx.enable_drop_target." + str(widget.uid),
            start=nursery.start,
            watch_for_drop=partial(_watch_for_drop, drag_classes, on_enter, on_leave, on_drop),
        ):
            if seen in touch.ud:
                return
            touch.ud[seen] = True
            if touch.is_mouse_scrolling:
                return
            start(watch_for_drop(widget, touch))

        widget.bind(on_touch_down=on_touch_xxx, on_touch_move=on_touch_xxx)
        try:
            await ak.sleep_forever()
        finally:
            widget.unbind(on_touch_down=on_touch_xxx, on_touch_move=on_touch_xxx)


async def _watch_for_drop(drag_classes, on_enter, on_leave, on_drop, drop_target, touch):
    ud = touch.ud
    async with ak.move_on_when(ud["kivyx_abandon"].wait()):
        tasks = await ak.wait_any(
            ud["kivyx_end"].wait(),
            ud["kivyx_exclusive_access"].wait_for_one_to_claim(),
        )
        if tasks[0].finished:
            return
        match tasks[1].result:
            case (dragged_widget, "drag_n_drop", drag_cls, drop_handlers) if drag_cls in drag_classes:
                pass
            case _:
                return

        is_inside = was_inside = False
        try:
            async with (
                ak.move_on_when(touch.ud["kivyx_end"].wait()),
                visibility_aware_touch_movements(drop_target, touch) as on_touch_move,
            ):
                while True:
                    is_inside = await on_touch_move()
                    if is_inside is was_inside:
                        continue
                    if is_inside:
                        on_enter(drop_target, touch, drag_cls, dragged_widget)
                    else:
                        on_leave(drop_target, touch, drag_cls, dragged_widget)
                    was_inside = is_inside
            if is_inside:
                drop_handlers.append(partial(on_drop, drop_target, touch, drag_cls, dragged_widget))
        finally:
            if is_inside:
                on_leave(drop_target, touch, drag_cls, dragged_widget)


class KXDropTargetBehavior:
    '''
    Mixin class that adds drop target behavior to widgets.
    '''

    drop_target_disabled = BooleanProperty(False)
    '''If either :attr:`~kivy.uix.widget.Widget.disabled` or :attr:`drop_target_disabled` is True,
    drop target behavior is disabled.
    '''

    drag_classes = ObjectProperty(ACCEPT_ANY)
    '''Drag classes accepted by this drop target. Must support the :class:`collections.abc.Collection` interface.'''

    def __init__(self, **kwargs):
        self.__main_task = ak.dummy_task
        self.register_event_type("on_drag_enter")
        self.register_event_type("on_drag_leave")
        self.register_event_type("on_drop")
        super().__init__(**kwargs)
        t = Clock.schedule_once(self.__reset, -1)
        self.bind(
            disabled=t,
            drop_target_disabled=t,
            drag_classes=t,
        )

    def on_drag_enter(self, touch, drag_cls, dragged_widget):
        '''
        Fired when a dragged widget enters the drop target.

        :param touch: in window coordinates.
        '''

    def on_drag_leave(self, touch, drag_cls, dragged_widget):
        '''
        Fired when a dragged widget leaves the drop target.

        For every ``on_drag_enter`` event, a corresponding ``on_drag_leave`` event is guaranteed,
        even if the drag is cancelled.

        :param touch: in window coordinates.
        '''

    def on_drop(self, touch, drag_cls, dragged_widget) -> bool:
        '''
        Fired when ``dragged_widget`` is dropped on this widget.

        :return:
            Return True to indicate that the drop was accepted. If False, the caller
            will continue searching for other drop targets.
        :param touch: in window coordinates.
        '''
        self.add_widget(dragged_widget)
        return True

    # Python's name mangling is weird. This method cannot be named '__reset'.
    def _KXDropTargetBehavior__reset(self, __):
        self.__main_task.cancel()
        if self.disabled or self.drop_target_disabled:
            return
        self.__main_task = ak.managed_start(enable_drop_target(
            self,
            drag_classes=self.drag_classes,
            on_enter=self.__dispatch_on_drag_enter_event,
            on_leave=self.__dispatch_on_drag_leave_event,
            on_drop=self.__dispatch_on_drop_event,
        ))

    @staticmethod
    def __dispatch_on_drag_enter_event(self, touch, drag_cls, dragged_widget):
        self.dispatch("on_drag_enter", touch, drag_cls, dragged_widget)

    @staticmethod
    def __dispatch_on_drag_leave_event(self, touch, drag_cls, dragged_widget):
        self.dispatch("on_drag_leave", touch, drag_cls, dragged_widget)

    @staticmethod
    def __dispatch_on_drop_event(self, touch, drag_cls, dragged_widget):
        return self.dispatch("on_drop", touch, drag_cls, dragged_widget)
