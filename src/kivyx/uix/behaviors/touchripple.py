__all__ = ("enable_touch_ripple_effect", )

from typing import TypedDict
from collections.abc import Callable, Sequence
from functools import partial
import math
from contextlib import closing, ExitStack

from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from kivy.animation import AnimationTransition
from kivy.graphics import (
    InstructionGroup, Color, Ellipse, StencilPush, StencilUse, StencilUnUse, StencilPop, Rectangle,
)
from kivy.input.motionevent import MotionEvent
from kivy.uix.widget import Widget
import asynckivy as ak
from asynckivy import anim_attrs, wait_any, start

from kivyx.touch_filters import is_colliding_and_not_wheel


class OptionalParams(TypedDict):
    """
    Just a type hint for the optional parameters of ``enable_touch_ripple_effect``.
    """
    relative_coordinates: bool
    clip_to_bounds: bool
    allow_multiple: bool
    initial_size: float
    final_size: float | None
    growth_duration: float
    fadeout_duration: float
    growth_curve: str
    fadeout_curve: str
    color: str | Sequence[float]
    fadeout_on_exclusive_access: bool


async def enable_touch_ripple_effect(
    widget, *,
    relative_coordinates=False,
    clip_to_bounds=True,
    touch_filter: Callable[[Widget, MotionEvent], bool]=is_colliding_and_not_wheel,
    allow_multiple=True,
    initial_size=dp(20),
    final_size: float | None=None,
    growth_duration=.3,
    fadeout_duration=.2,
    growth_curve="linear",
    fadeout_curve="linear",
    color: str | Sequence[float]="#FFFFFF44",
    fadeout_on_exclusive_access=True,
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
        The initial diameter from which ripples grow. Defaults to ``dp(20)``.

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
            add(bbox := Rectangle(size=widget.size))
            add(StencilUse())
            add(ripple_pane)
            add(StencilUnUse())
            add(bbox)
            add(StencilPop())
            stack.enter_context(ak.sync_attr((widget, "size"), (bbox, "size")))
            if not relative_coordinates:
                bbox.pos = widget.pos
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
