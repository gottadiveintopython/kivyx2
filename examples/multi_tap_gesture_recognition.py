from kivy.lang import Builder
from kivy.uix.label import Label
from kivy.app import App


from kivyx.uix.behaviors.tap import KXTapGestureRecognizer, KXMultiTapGestureRecognizer
from kivyx.uix.behaviors.touchripple import KXTouchRippleBehavior


class MultiTapButton(KXTouchRippleBehavior, KXMultiTapGestureRecognizer,  Label):
    def on_multi_tap(self, n_taps, touches):
        if n_taps == 1:
            print("single-tapped.")
        elif n_taps == 2:
            print("double-tapped.")
        else:
            print(f"{n_taps}-tapped.")


class SingleTapButton(KXTouchRippleBehavior, KXTapGestureRecognizer,  Label):
    def on_tap(self, touch):
        print("tapped.")


KV_CODE = '''
<MultiTapButton, SingleTapButton>:
    canvas.before:
        StencilPush:
        RoundedRectangle:
            pos: self.pos
            size: self.size
        StencilUse:
        Color:
            rgba: (.2, .2, .4, 1) if self.disabled else (.4, .2, .8, 1)
        Rectangle:
            pos: self.pos
            size: self.size
    canvas.after:
        StencilUnUse:
        RoundedRectangle:
            pos: self.pos
            size: self.size
        StencilPop:

BoxLayout:
    padding: 40, 40
    spacing: 40
    orientation: 'vertical'
    MultiTapButton:
        font_size: 30
        text: "This recognizes multi-tap gestures."
        disabled: not switch.active
        tap_max_count: 7
    SingleTapButton:
        font_size: 30
        text: "This one doesn't."
        disabled: not switch.active
        ripple_color: "#00FF0066"
    Switch:
        id: switch
        active: True
'''


class SampleApp(App):
    def build(self):
        return Builder.load_string(KV_CODE)


if __name__ == '__main__':
    SampleApp(title='multi-tap').run()
