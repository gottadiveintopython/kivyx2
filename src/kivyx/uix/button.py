__all__ = ("KXButton", )

from kivy.properties import ColorProperty
from kivy.lang import Builder
from kivy.uix.label import Label
import asynckivy as ak

from kivyx.touch_filters import is_colliding_and_not_wheel
from kivyx.uix.behaviors.tap import enable_tap_gesture_recognition
from kivyx.uix.behaviors.touchripple import enable_touch_ripple_effect


class KXButton(Label):
    '''
    A simple button for use in examples.

    .. warning::
        This button ignores the :attr:`~kivy.uix.widget.Widget.disabled` property
        and responds to taps even when it is set to True.
    '''
    __events__ = ("on_tap", )
    background_color = ColorProperty((.4, .2, .8, 1))
    background_disabled_color = ColorProperty((.2, .2, .4, 1))
    on_touch_down = on_touch_move = on_touch_up = is_colliding_and_not_wheel

    def on_tap(self, touch):
        pass

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        ak.managed_start(enable_tap_gesture_recognition(self, consume_touch=False, on_tap=_dispatch_event))
        ak.managed_start(enable_touch_ripple_effect(self, clip_to_bounds=False))


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
