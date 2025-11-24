__all__ = ("KXTouchRippleBehavior", )

from typing import Self
from functools import partial
import math
from kivy.clock import Clock
from kivy.animation import AnimationTransition
from kivy.properties import NumericProperty, StringProperty, ColorProperty, BooleanProperty, OptionProperty
from kivy.graphics import InstructionGroup, Color, Ellipse
import asynckivy as ak
from asynckivy import anim_attrs, run_as_main

from kivyx.touch_filters import is_opos_colliding_and_not_wheel


class KXTouchRippleBehavior:
    '''
    Unlike the official :class:`~kivy.uix.behaviors.touchripple.TouchRippleBehavior`,
    this one does not clip its drawing area.
    '''

    ripple_initial_size = NumericProperty('20dp')
    '''The initial diameter from which ripples grow.'''

    ripple_final_size = NumericProperty(None, allownone=True)
    '''The final diameter at which ripples stop growing. If set to None (the default),
    it becomes the minimum size required to cover the widget.'''

    ripple_growth_duration = NumericProperty(.3)
    '''The animation duration taken to grow ripples.'''

    ripple_fadeout_duration = NumericProperty(.2)
    '''The animation duration taken to fade out ripples.'''

    ripple_growth_curve = StringProperty("linear")
    '''The animation curve used to grow ripples.'''

    ripple_fadeout_curve = StringProperty("linear")
    '''The animation curve used to fade out ripples.'''

    ripple_color = ColorProperty("#FFFFFF44")

    ripple_allow_multiple = BooleanProperty(True)
    '''Whether multiple ripples can be shown simultaneously via multi-touch.'''

    ripple_fadeout_on_exclusive_access = BooleanProperty(True)
    '''If set to True (the default), ripples begin fading out when exclusive access to
    their corresponding touches is claimed.'''

    ripple_draw_on = OptionProperty("canvas", options=("canvas", "canvas.before", "canvas.after"))
    '''The canvas on which ripples are drawn.
    '''

    def __init__(self, **kwargs):
        self.__main_task = ak.dummy_task
        t = Clock.schedule_once(self.__reset)
        f = self.fbind
        f("disabled", t)
        f("ripple_growth_curve", t)
        f("ripple_fadeout_curve", t)
        f("ripple_allow_multiple", t)
        f("ripple_fadeout_on_exclusive_access", t)
        f("ripple_draw_on", t)
        super().__init__(**kwargs)

    # Python's name mangling is weird. This method cannot be named '__reset'.
    def _KXTouchRippleBehavior__reset(self, __):
        self.__main_task.cancel()
        if self.disabled:
            return
        self.__main_task = ak.managed_start(self.__main())

    async def __main(self):
        on_touch_down = partial(ak.event, self, "on_touch_down", filter=is_opos_colliding_and_not_wheel)
        draw_target = self.canvas
        match self.ripple_draw_on:
            case "canvas":
                pass
            case "canvas.after":
                draw_target = draw_target.after
            case "canvas.before":
                draw_target = draw_target.before
        generate_ripple = partial(
            self.__generate_ripple, draw_target,
            "kivyx_exclusive_access" if self.ripple_fadeout_on_exclusive_access else "kivyx_end_event",
            getattr(AnimationTransition, self.ripple_growth_curve),
            getattr(AnimationTransition, self.ripple_fadeout_curve),
            self,
        )
        if self.ripple_allow_multiple:
            async with ak.open_nursery() as nursery:
                start = nursery.start
                while True:
                    __, touch = await on_touch_down()
                    start(generate_ripple(touch))
        else:
            while True:
                __, touch = await on_touch_down()
                await generate_ripple(touch)

    @staticmethod
    async def __generate_ripple(draw_target, fadeout_trigger_key, growth_curve, fadeout_curve, self: Self, touch):
        cx, cy = self.to_local(*touch.opos)  # center of the ripple
        diameter = self.ripple_initial_size
        radius = diameter / 2
        ellipse = Ellipse(
            size=(diameter, diameter),
            pos=(cx - radius, cy - radius),
        )

        draw_target.add(ig := InstructionGroup())
        try:
            ig.add(color := Color(*self.ripple_color))
            ig.add(ellipse)
            final_diameter = self.ripple_final_size
            if final_diameter is None:
                final_radius = _calc_enclosing_circle_radius(touch.opos, self)
                final_diameter = final_radius * 2
            else:
                final_radius = final_diameter / 2

            async with run_as_main(touch.ud[fadeout_trigger_key].wait()):
                await anim_attrs(
                    ellipse,
                    size=(final_diameter, final_diameter, ),
                    pos=(cx - final_radius, cy - final_radius),
                    duration=self.ripple_growth_duration,
                    transition=growth_curve,
                )
            await anim_attrs(color, a=0, duration=self.ripple_fadeout_duration, transition=fadeout_curve)
        finally:
            draw_target.remove(ig)


def _calc_enclosing_circle_radius(center_of_circle, widget, max=max, sqrt=math.sqrt):
    '''
    Calculates the radius of a minimum enclosing circle for a given widget.

    .. code-block::

        radius = _calc_enclosing_circle_radius(center_of_circle, widget)

    .. warning::

        The ``center_of_circle`` must be inside the ``widget``; otherwise, the result will be incorrect.
    '''
    x, y = center_of_circle
    return sqrt(max(x - widget.x, widget.right - x) ** 2 + max(y - widget.y, widget.top - y) ** 2)
