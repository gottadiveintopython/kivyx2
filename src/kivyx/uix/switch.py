__all__ = ("KXSwitch", )

import itertools
from kivy.properties import (
    ColorProperty, BooleanProperty, NumericProperty, ReferenceListProperty, AliasProperty,
    StringProperty,
)
from kivy.clock import Clock
from kivy.animation import AnimationTransition
from kivy.lang import Builder
from kivy.uix.widget import Widget
from kivyx.uix.behaviors.tap import KXTapGestureRecognizer
import asynckivy as ak


Builder.load_string("""
<KXSwitch>:
    size_hint_min: self.track_size
    canvas:
        PushMatrix:
        Translate:
            xy: self.center
        Color:
            rgba: self._track_color
        RoundedRectangle:
            radius: (self._track_half_height, ) * 2
            pos: -self._track_half_width, -self._track_half_height
            size: self.track_size
        Color:
            rgba: self._thumb_color
        Ellipse:
            pos:
                (
                self._thumb_inactive_x + self._anim_progress * self._thumb_movement_x,
                self._padding - self._track_half_height,
                )
            size: (self.track_height - self._padding * 2, ) * 2
        PopMatrix:
""")


class KXSwitch(KXTapGestureRecognizer, Widget):
    '''
    Inspired by Flutter's `CupertinoSwitch <https://youtu.be/24tg_N4sdMQ>`__.
    '''

    active = BooleanProperty(False)
    anim_transition = StringProperty("linear")
    anim_duration = NumericProperty(.2)
    _anim_progress = NumericProperty(0.)
    _padding = AliasProperty(
        lambda self: self.track_height / 16,
        bind=("track_height", ), cache=True)

    track_active_color = ColorProperty("#B66AF7")
    track_inactive_color = ColorProperty("#888888")
    track_disabled_color = ColorProperty("#444444")
    _track_color = ColorProperty()
    track_width = NumericProperty("64sp")
    track_height = NumericProperty("32sp")
    track_size = ReferenceListProperty(track_width, track_height)
    _track_half_width = AliasProperty(lambda self: self.track_width / 2, bind=("track_width", ), cache=True)
    _track_half_height = AliasProperty(lambda self: self.track_height / 2, bind=("track_height", ), cache=True)

    thumb_active_color = ColorProperty("#FFFFFF")
    thumb_inactive_color = ColorProperty("#FFFFFF")
    thumb_disabled_color = ColorProperty("#666666")
    _thumb_color = ColorProperty()
    _thumb_inactive_x = AliasProperty(
        lambda self: self._padding - self._track_half_width,
        bind=("_padding", "_track_half_width"), cache=True)
    _thumb_movement_x = AliasProperty(
        lambda self: self.track_width - self.track_height,
        bind=("track_width", "track_height"), cache=True)

    def collide_point(self, x, y) -> bool:
        hw = self._track_half_width
        hh = self._track_half_height
        cx, cy = self.center
        return cx - hw <= x < cx + hw and cy - hh <= y < cy + hh

    def __init__(self, **kwargs):
        self._main_task = ak.dummy_task
        super().__init__(**kwargs)
        f = self.fbind
        t = Clock.schedule_once(self._reset, -1)
        f("disabled", t)
        f("anim_transition", t)
        f("thumb_active_color", t)
        f("track_active_color", t)
        f("thumb_inactive_color", t)
        f("track_inactive_color", t)

    def _reset(self, dt):
        self._main_task.cancel()
        self._main_task = ak.managed_start(self._main())

    async def _main(self):
        if self.disabled:
            self._thumb_color = self.thumb_disabled_color
            self._track_color = self.track_disabled_color
            with (
                ak.sync_attr((self, "thumb_disabled_color"), (self, "_thumb_color")),
                ak.sync_attr((self, "track_disabled_color"), (self, "_track_color")),
            ):
                while True:
                    self._anim_progress = 1. if self.active else 0.
                    await ak.event(self, "active")
        anim_transition = getattr(AnimationTransition, self.anim_transition)
        value_sets = itertools.cycle((
            # (active, anim_progress, track_color, thumb_color)
            (False, 0., self.track_inactive_color, self.thumb_inactive_color),
            (True, 1., self.track_active_color, self.thumb_active_color),
        ))
        if self.active:
            next(value_sets)
        active, anim_progress, track_color, thumb_color = next(value_sets)
        self.active = active
        self._anim_progress = anim_progress
        self._track_color = track_color
        self._thumb_color = thumb_color

        for active, anim_progress, track_color, thumb_color in value_sets:
            await ak.wait_any(ak.event(self, "on_tap"), ak.event(self, "active"))
            self.active = active
            await ak.anim_attrs(
                self,
                _anim_progress=anim_progress,
                _thumb_color=thumb_color,
                _track_color=track_color,
                duration=self.anim_duration,
                transition=anim_transition,
            )
