from collections.abc import Awaitable
from functools import partial

from kivy.clock import Clock
from kivy.properties import BooleanProperty, ObjectProperty
from kivy.graphics import Color, Rectangle
from kivy.uix.widget import Widget
import asynckivy as ak

from kivyx.utils import copy_layout_state, visibility_aware_touch_movements, find_child_with_index_at
from ._common import ACCEPT_ANY, DragClasses


async def enable_drop_target_with_insertion_indicator(
    layout, *,
    drag_classes: DragClasses=ACCEPT_ANY,
    spacer_widgets: list[Widget] | int=1,
):
    '''
    Enables ``layout`` to act as a drop target with an insertion indicator until the returned coroutine is cancelled.

    While a widget is dragged over the layout, a spacer widget is temporarily inserted to indicate
    where the widget would be inserted if it were dropped at that moment.

    :param drag_classes:
        Drag classes accepted by this drop target.

    :param spacer_widgets:
        Widgets used as spacers during dragging. The number of spacer widgets determines the maximum number of
        simultaneous drags that can be handled. If an integer is provided, that many spacer widgets are created
        internally.
    '''
    layout = layout.__self__
    if isinstance(spacer_widgets, int):
        spacer_widgets = [_create_default_spacer() for _ in range(spacer_widgets)]
    async with ak.open_nursery() as nursery:
        def on_touch_xxx(
            layout, touch,
            seen="kivyx.enable_drop_target_with_insertion_indicator." + str(layout.uid),
            start=nursery.start,
            watch_for_drop=partial(_watch_for_drop, spacer_widgets, drag_classes),
        ):
            if seen in touch.ud:
                return
            touch.ud[seen] = True
            if touch.is_mouse_scrolling:
                return
            start(watch_for_drop(layout, touch))

        layout.bind(on_touch_down=on_touch_xxx, on_touch_move=on_touch_xxx)
        try:
            await ak.sleep_forever()
        finally:
            layout.unbind(on_touch_down=on_touch_xxx, on_touch_move=on_touch_xxx)


def _create_default_spacer() -> Widget:
    w = Widget()
    w.canvas.add(Color(.2, .2, .2, .7))
    w.canvas.add(rect := Rectangle())
    ak.sync_attr((w, "pos"), (rect, "pos"))
    ak.sync_attr((w, "size"), (rect, "size"))
    return w


async def _watch_for_drop(spacer_widgets, drag_classes, layout, touch):
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
        insert_idx = await _show_insertion_indicator(spacer_widgets, layout, touch, dragged_widget)
        if insert_idx is not None:
            drop_handlers.append(partial(_add_widget_and_return_true, layout, dragged_widget, insert_idx))


def _add_widget_and_return_true(layout, widget, index):
    layout.add_widget(widget, index=index)
    return True


async def _show_insertion_indicator(spacer_widgets, layout, touch, dragged_widget) -> Awaitable[int | None]:
    '''
    Temporarily inserts a spacer widget to show where ``dragged_widget`` would be placed
    in ``layout`` when ``touch`` is released.

    :returns: The index of the spacer widget in ``layout.children`` when ``touch`` ends,
        or ``None`` if no spacer is present.
    '''
    # LOAD_FAST
    children = layout.children
    add_widget = layout.add_widget
    remove_widget = layout.remove_widget
    to_widget = layout.to_widget
    find_child_with_idx_at = find_child_with_index_at

    if spacer_widgets and dragged_widget in children:
        spacer = spacer_widgets.pop()
        copy_layout_state(dragged_widget, spacer)
        add_widget(spacer, index=children.index(dragged_widget))
    else:
        spacer = None

    try:
        async with (
            ak.move_on_when(touch.ud["kivyx_end"].wait()),
            visibility_aware_touch_movements(layout, touch) as on_touch_move,
        ):
            was_inside = False
            while True:
                is_inside = await on_touch_move()
                if is_inside:
                    if spacer is None:
                        if spacer_widgets:
                            spacer = spacer_widgets.pop()
                            copy_layout_state(dragged_widget, spacer)
                        else:
                            continue
                    child, idx = find_child_with_idx_at(children, *to_widget(*touch.pos))
                    if child is spacer:
                        continue
                    remove_widget(spacer)
                    if child is None:
                        idx = 0
                    add_widget(spacer, index=idx)
                elif was_inside and spacer is not None:
                    remove_widget(spacer)
                    spacer_widgets.append(spacer)
                    spacer = None
                was_inside = is_inside
    finally:
        if spacer is None:
            idx = None
        else:
            if spacer.parent is None:
                idx = None
            else:
                idx = children.index(spacer)
                remove_widget(spacer)
            spacer_widgets.append(spacer)
    return idx


class KXDropTargetBehaviorWithInsertionIndicator:
    '''
    Mixin class that adds drop target behavior with insertion indicator to layouts.
    '''

    drop_target_disabled = BooleanProperty(False)
    '''If either :attr:`~kivy.uix.widget.Widget.disabled` or :attr:`drop_target_disabled` is True,
    drop target behavior is disabled.
    '''

    drag_classes = ObjectProperty(ACCEPT_ANY)
    '''See :func:`enable_drop_target_with_insertion_indicator`.'''

    drop_target_spacer_widgets = ObjectProperty(1)
    '''See :func:`enable_drop_target_with_insertion_indicator`.'''

    def __init__(self, **kwargs):
        self.__main_task = ak.dummy_task
        super().__init__(**kwargs)
        t = Clock.schedule_once(self.__reset, -1)
        self.bind(
            disabled=t,
            drop_target_disabled=t,
            drag_classes=t,
            drop_target_spacer_widgets=t,
        )

    # Python's name mangling is weird. This method cannot be named '__reset'.
    def _KXDropTargetBehaviorWithInsertionIndicator__reset(self, __):
        self.__main_task.cancel()
        if self.disabled or self.drop_target_disabled:
            return
        self.__main_task = ak.managed_start(enable_drop_target_with_insertion_indicator(
            self,
            drag_classes=self.drag_classes,
            spacer_widgets=self.drop_target_spacer_widgets,
        ))

