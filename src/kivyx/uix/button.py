__all__ = ("KXButton", "KXMultiTapButton", )

from kivy.properties import ColorProperty
from kivy.lang import Builder
from kivy.uix.label import Label


from kivyx.uix.behaviors.tap import KXTapGestureRecognizer, KXMultiTapGestureRecognizer
from kivyx.uix.behaviors.touchripple import KXTouchRippleBehavior


class KXButton(KXTouchRippleBehavior, KXTapGestureRecognizer, Label):
    background_color = ColorProperty((.4, .2, .8, 1))
    background_disabled_color = ColorProperty((.2, .2, .4, 1))


class KXMultiTapButton(KXTouchRippleBehavior, KXMultiTapGestureRecognizer, Label):
    background_color = ColorProperty((.4, .2, .8, 1))
    background_disabled_color = ColorProperty((.2, .2, .4, 1))


Builder.load_string('''
<KXButton, KXMultiTapButton>:
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
