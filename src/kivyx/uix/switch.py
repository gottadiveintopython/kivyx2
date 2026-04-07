__all__ = ("KXSwitch", )

from kivy.properties import (
    ColorProperty, BooleanProperty, NumericProperty, ReferenceListProperty,
)
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.uix.widget import Widget
import asynckivy as ak
from kivyx.uix.behaviors.tap import enable_tap_gesture_recognition

Builder.load_string("""
<KXSwitch>:
    _track_half_width: self.track_width / 2
    _track_half_height: self.track_height / 2
    _padding: self.track_height / 16
    _thumb_active_x: self._track_half_width - self.track_height + self._padding
    _thumb_inactive_x: self._padding - self._track_half_width
    _thumb_y: self._padding - self._track_half_height
    _track_color:
        (
        self.track_disabled_color if self.disabled else
        (self.track_active_color if self.active else self.track_inactive_color)
        )
    _thumb_x: self._thumb_active_x if self.active else self._thumb_inactive_x
    _thumb_color:
        (
        self.thumb_disabled_color if self.disabled else
        (self.thumb_active_color if self.active else self.thumb_inactive_color)
        )
    canvas:
        PushMatrix:
        Translate:
            xy: self.center
        Color:
            group: "smoothing_target"
        RoundedRectangle:
            radius: (self._track_half_height, ) * 2
            pos: -self._track_half_width, -self._track_half_height
            size: self.track_size
        Color:
            group: "smoothing_target"
        Ellipse:
            group: "smoothing_target"
            size: (self.track_height - self._padding * 2, ) * 2
        PopMatrix:
""")


class KXSwitch(Widget):
    '''
    Inspired by Flutter's `CupertinoSwitch <https://youtu.be/24tg_N4sdMQ>`__.
    Unlike the official :class:`~kivy.uix.switch.Switch`, the ``collide_point`` method
    checks for collision against the track area rather than the entire widget.
    '''

    active = BooleanProperty(False)
    '''Whether the switch is on (True) or off (False).'''

    track_active_color = ColorProperty("#B66AF7")
    '''The color to use for the track when the switch is on.'''

    track_inactive_color = ColorProperty("#888888")
    '''The color to use for the track when the switch is off.'''

    track_disabled_color = ColorProperty("#444444")
    '''The color to use for the track when the switch is disabled.'''

    _track_color = ColorProperty()

    track_width = NumericProperty("64sp")
    '''The width of the switch track.'''

    track_height = NumericProperty("32sp")
    '''The height of the switch track.'''

    track_size = ReferenceListProperty(track_width, track_height)
    '''
    The size of the switch track. (:class:`~kivy.properties.ReferenceListProperty` of
    :attr:`track_width` and :attr:`track_height`)
    '''

    _track_half_width = NumericProperty()
    _track_half_height = NumericProperty()
    _padding = NumericProperty()

    minimum_width = track_width
    '''An alias for :attr:`track_width`.'''

    minimum_height = track_height
    '''An alias for :attr:`track_height`.'''

    minimum_size = track_size
    '''An alias for :attr:`track_size`.'''

    thumb_active_color = ColorProperty("#FFFFFF")
    '''The color to use on the thumb when the switch is on.'''

    thumb_inactive_color = ColorProperty("#FFFFFF")
    '''The color to use on the thumb when the switch is off.'''

    thumb_disabled_color = ColorProperty("#666666")
    '''The color to use on the thumb when the switch is disabled.'''

    _thumb_color = ColorProperty()

    _thumb_active_x = NumericProperty()
    _thumb_inactive_x = NumericProperty()
    _thumb_x = NumericProperty()
    _thumb_y = NumericProperty()
    _thumb_pos = ReferenceListProperty(_thumb_x, _thumb_y)

    def collide_point(self, x, y) -> bool:
        hw = self._track_half_width
        hh = self._track_half_height
        cx, cy = self.center
        return cy - hh <= y < cy + hh and cx - hw <= x < cx + hw

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._main_task = ak.dummy_task
        self.fbind("disabled", Clock.schedule_once(self._reset, -1))
        Clock.schedule_once(self._setup_smoothing, -1)

    def _setup_smoothing(self, __):
        track_color, thumb_color, thumb_ellipse = self.canvas.get_group("smoothing_target")
        ak.smooth_attr((self, "_thumb_color"), (thumb_color, "rgba"), min_diff=0.02)
        ak.smooth_attr((self, "_track_color"), (track_color, "rgba"), min_diff=0.02)
        ak.smooth_attr((self, "_thumb_pos"), (thumb_ellipse, "pos"))

    def _reset(self, __):
        self._main_task.cancel()
        if self.disabled:
            return
        self._main_task = ak.managed_start(enable_tap_gesture_recognition(
            self,
            track_multiple_touches=False,
            consume_touch=True,
            on_tap=self._toggle_onoff,
        ))

    @staticmethod
    def _toggle_onoff(switch, touch):
        switch.active = not switch.active
