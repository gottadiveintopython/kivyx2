__all__ = ("enable_touch_ripple_effect", "KXTouchRippleBehavior", )

from collections.abc import Callable, Sequence
from functools import partial
import math
from contextlib import closing, ExitStack

from kivy.metrics import dp
from kivy.clock import Clock
from kivy.utils import get_color_from_hex
from kivy.animation import AnimationTransition
from kivy.properties import NumericProperty, StringProperty, ColorProperty, BooleanProperty, ObjectProperty
from kivy.graphics import (
    InstructionGroup, Color, Ellipse, StencilPush, StencilUse, StencilUnUse, StencilPop, Rectangle,
)
from kivy.input.motionevent import MotionEvent
from kivy.uix.widget import Widget
import asynckivy as ak
from asynckivy import anim_attrs, wait_any, start

from kivyx.touch_filters import is_colliding_and_not_wheel

class defaults:
    relative_coordinates = False
    clip_to_bounds = True
    allow_multiple = True
    initial_size = dp(20)
    final_size = None
    growth_duration = .3
    fadeout_duration = .2
    growth_curve = "linear"
    fadeout_curve = "linear"
    color = "#FFFFFF44"
    fadeout_on_exclusive_access = True


async def enable_touch_ripple_effect(
    widget, *,
    relative_coordinates=defaults.relative_coordinates,
    clip_to_bounds=defaults.clip_to_bounds,
    touch_filter: Callable[[Widget, MotionEvent], bool]=is_colliding_and_not_wheel,
    allow_multiple=defaults.allow_multiple,
    initial_size=defaults.initial_size,
    final_size: float | None=defaults.final_size,
    growth_duration=defaults.growth_duration,
    fadeout_duration=defaults.fadeout_duration,
    growth_curve: str=defaults.growth_curve,
    fadeout_curve: str=defaults.fadeout_curve,
    color: str | Sequence[float]=defaults.color,
    fadeout_on_exclusive_access=defaults.fadeout_on_exclusive_access,
):
    '''
    Enables the touch ripple effect for a widget until the returned coroutine is cancelled.

    :param relative_coordinates:
        Must be set to True if the widget uses relative coordinates
        (e.g. :class:`~kivy.uix.relativelayout.RelativeLayout`, :class:`~kivy.uix.scatter.Scatter`).

    :param clip_to_bounds:
        Whether ripples are clipped to the widget's bounding box. You may want to set this to False
        if the widget already clips its contents on its own.

    :param touch_filter:
        Any touch whose ``on_touch_down`` event does not pass this filter is ignored.
        Defaults to :func:`~kivyx.touch_filters.is_colliding_and_not_wheel`.

    :param allow_multiple:
        Whether multiple ripples can be shown simultaneously via multi-touch.

    :param initial_size:
        The initial diameter from which ripples grow.

    :param final_size:
        The final diameter at which ripples stop growing. If set to None (the default),
        it is computed as the minimum size required to cover the widget.

    :param growth_duration:
        The animation duration taken to grow ripples.

    :param fadeout_duration:
        The animation duration taken to fade out ripples.

    :param growth_curve:
        The animation curve used to grow ripples.

    :param fadeout_curve:
        The animation curve used to fade out ripples.

    :param color:
        The color of the ripples. Can be a hex string or an RGBA sequence.

    :param fadeout_on_exclusive_access:
        If set to True (the default), ripples begin fading out when exclusive access to their corresponding
        touches is claimed. If set to False, ripples begin fading out only when their corresponding touches end.
    '''
    with ExitStack() as stack:
        ripple_pane = root_pane = InstructionGroup()
        if clip_to_bounds:
            root_pane = InstructionGroup()
            add = root_pane.add
            add(StencilPush())
            add(bbox := Rectangle())
            add(StencilUse())
            add(ripple_pane)
            add(StencilUnUse())
            add(bbox)
            add(StencilPop())
            stack.enter_context(ak.sync_attr((widget, "size"), (bbox, "size")))
            if not relative_coordinates:
                stack.enter_context(ak.sync_attr((widget, "pos"), (bbox, "pos")))
        widget.canvas.after.insert(0, root_pane)
        stack.callback(widget.canvas.after.remove, root_pane)

        on_touch_down = partial(ak.event, widget, "on_touch_down", filter=touch_filter)
        spawn_ripple = partial(
            _spawn_ripple,
            widget,
            ripple_pane,
            getattr(AnimationTransition, growth_curve),
            getattr(AnimationTransition, fadeout_curve),
            growth_duration, fadeout_duration,
            initial_size, initial_size / 2,
            final_size, None if final_size is None else (final_size / 2.),
            get_color_from_hex(color) if isinstance(color, str) else color,
            fadeout_on_exclusive_access,
        )
        if allow_multiple:
            async with ak.open_nursery() as nursery:
                while True:
                    __, touch = await on_touch_down()
                    nursery.start(spawn_ripple(touch))
        else:
            while True:
                __, touch = await on_touch_down()
                await spawn_ripple(touch)


async def _spawn_ripple(
    widget,
    ripple_pane,
    growth_curve,
    fadeout_curve,
    growth_duration, fadeout_duration,
    initial_diameter, initial_radius,
    final_diameter, final_radius,
    color,
    fadeout_on_exclusive_access,
    touch,
):
    cx, cy = widget.to_local(*touch.opos)  # center of the ripple
    ellipse = Ellipse(
        size=(initial_diameter, initial_diameter),
        pos=(cx - initial_radius, cy - initial_radius),
    )

    ud = touch.ud
    ripple_pane.add(ig := InstructionGroup())
    try:
        ig.add(color := Color(*color))
        ig.add(ellipse)
        if final_diameter is None:
            final_radius = _calc_enclosing_circle_radius(touch.opos, widget)
            final_diameter = final_radius * 2.
        with closing(start(anim_attrs(
            ellipse,
            size=(final_diameter, final_diameter, ),
            pos=(cx - final_radius, cy - final_radius),
            duration=growth_duration,
            transition=growth_curve,
        ))):
            await wait_any(
                ud["kivyx_end"].wait(),
                ud["kivyx_abandon"].wait(),
                ud["kivyx_exclusive_access"].wait_for_one_to_claim() if \
                    fadeout_on_exclusive_access else ak.sleep_forever(),
            )
        await anim_attrs(color, a=0, duration=fadeout_duration, transition=fadeout_curve)
    finally:
        ripple_pane.remove(ig)


class KXTouchRippleBehavior:
    '''
    A mixin class that adds touch ripple effect to widgets.

    (Some docstrings in this class are written in Japanese because the corresponding English
    documentation is already available in :func:`enable_touch_ripple_effect`.)
    '''

    ripple_disabled = BooleanProperty(False)
    '''If either :attr:`~kivy.uix.widget.Widget.disabled` or :attr:`ripple_disabled` is True,
    ripple effect is disabled.
    '''

    ripple_relative_coordinates = BooleanProperty(defaults.relative_coordinates)
    '''
    相対座標系(例：:class:`~kivy.uix.relativelayout.RelativeLayout`, :class:`~kivy.uix.scatter.Scatter`)
    のwidgetと合成する場合は真にしてください。
    '''

    ripple_clip_to_bounds = BooleanProperty(defaults.clip_to_bounds)
    '''
    波紋の描画をwidget内に収めるか否か。widgetが既にそのような事を自身で行っている場合は偽にした方が効率面で吉。
    '''

    ripple_touch_filter = ObjectProperty(is_colliding_and_not_wheel)
    '''
    ``on_touch_down`` イベントがこの選別をくぐり抜けると波紋が発生する。
    既定値は :func:`~kivyx.touch_filters.is_colliding_and_not_wheel`。
    '''

    ripple_initial_size = NumericProperty(defaults.initial_size)
    '''波紋発生時の直径'''

    ripple_final_size = NumericProperty(defaults.final_size, allownone=True)
    '''波紋が広がりきった時の直径。None(既定値)の場合は丁度widgetを覆う大きさ。'''

    ripple_growth_duration = NumericProperty(defaults.growth_duration)
    '''波紋が広がるのにかかる時間'''

    ripple_fadeout_duration = NumericProperty(defaults.fadeout_duration)
    '''波紋が薄まるのにかかる時間'''

    ripple_growth_curve = StringProperty(defaults.growth_curve)
    '''波紋の広がり方の緩急'''

    ripple_fadeout_curve = StringProperty(defaults.fadeout_curve)
    '''波紋の薄まり方の緩急'''

    ripple_color = ColorProperty(defaults.color)
    '''波紋の色'''

    ripple_allow_multiple = BooleanProperty(defaults.allow_multiple)
    '''複数のタッチによって複数の波紋を発生させるか否か'''

    ripple_fadeout_on_exclusive_access = BooleanProperty(defaults.fadeout_on_exclusive_access)
    '''
    誰かがタッチへの排他アクセスを得た時に波紋が薄まり始めるか否か。
    偽の場合は指が離れない限り波紋は薄まり始めない。
    '''

    def __init__(self, **kwargs):
        self.__main_task = ak.dummy_task
        t = Clock.schedule_once(self.__reset, -1)
        self.bind(
            disabled=t,
            ripple_disabled=t,
            ripple_relative_coordinates=t,
            ripple_clip_to_bounds=t,
            ripple_touch_filter=t,
            ripple_initial_size=t,
            ripple_final_size=t,
            ripple_growth_duration=t,
            ripple_fadeout_duration=t,
            ripple_growth_curve=t,
            ripple_fadeout_curve=t,
            ripple_color=t,
            ripple_allow_multiple=t,
            ripple_fadeout_on_exclusive_access=t,
        )
        super().__init__(**kwargs)

    # Python's name mangling is weird. This method cannot be named '__reset'.
    def _KXTouchRippleBehavior__reset(self, __):
        self.__main_task.cancel()
        if self.disabled or self.ripple_disabled:
            return
        self.__main_task = ak.managed_start(enable_touch_ripple_effect(
            self,
            relative_coordinates=self.ripple_relative_coordinates,
            clip_to_bounds=self.ripple_clip_to_bounds,
            touch_filter=self.ripple_touch_filter,
            allow_multiple=self.ripple_allow_multiple,
            initial_size=self.ripple_initial_size,
            final_size=self.ripple_final_size,
            growth_duration=self.ripple_growth_duration,
            fadeout_duration=self.ripple_fadeout_duration,
            growth_curve=self.ripple_growth_curve,
            fadeout_curve=self.ripple_fadeout_curve,
            color=self.ripple_color,
            fadeout_on_exclusive_access=self.ripple_fadeout_on_exclusive_access,
        ))


def _calc_enclosing_circle_radius(center_of_circle, widget, max=max, hypot=math.hypot):
    '''
    Calculates the minimum radius required for a circle centered at the given position to fully
    enclose the given widget.

    .. code-block::

        radius = _calc_enclosing_circle_radius(center_of_circle, widget)

    .. warning::

        The ``center_of_circle`` must be inside the ``widget``; otherwise, the result will be incorrect.
    '''
    x, y = center_of_circle
    return hypot(max(x - widget.x, widget.right - x), max(y - widget.y, widget.top - y))
