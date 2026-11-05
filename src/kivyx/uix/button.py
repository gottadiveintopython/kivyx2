__all__ = ("KXButton", )

from contextlib import ExitStack
from kivy.properties import ColorProperty
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.uix.label import Label
import asynckivy as ak

from kivyx.utils import noop
from kivyx.touch_filters import is_colliding_and_not_wheel
from kivyx.uix.behaviors.tap import enable_tap_gesture_recognition
from kivyx.uix.behaviors.touchripple import enable_touch_ripple_effect


class KXButton(Label):
    '''
    A simple button intended for use in examples.
    '''
    __events__ = ("on_tap", )
    background_color = ColorProperty((.4, .2, .8, 1))
    background_disabled_color = ColorProperty((.2, .2, .4, 1))
    on_touch_down = on_touch_move = on_touch_up = is_colliding_and_not_wheel

    _deactivate = noop

    def on_tap(self, touch):
        pass

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.fbind("disabled", Clock.schedule_once(self._reset, -1))

    def _reset(self, __):
        self._deactivate()
        if self.disabled:
            return
        with ExitStack() as stack:
            defer = stack.callback
            defer(ak.start(enable_tap_gesture_recognition(self, consume_touch=False, on_tap=_dispatch_event)).cancel)
            defer(ak.start(enable_touch_ripple_effect(self, clip_to_bounds=False)).cancel)
            self._deactivate = stack.pop_all().close


def _dispatch_event(button, touch):
    button.dispatch("on_tap", touch)


Builder.load_string('''
<KXButton>:
    canvas.before:
        StencilPush:
        RoundedRectangle:
            pos: self.pos
            size: self.size
        StencilUse:
        Color:
            rgba: self.background_disabled_color if self.disabled else self.background_color
        Rectangle:
            pos: self.pos
            size: self.size
    canvas.after:
        StencilUnUse:
        RoundedRectangle:
            pos: self.pos
            size: self.size
        StencilPop:
''')
