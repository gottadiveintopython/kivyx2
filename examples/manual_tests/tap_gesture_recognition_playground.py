from kivy.app import App
from kivy.lang import Builder
import kivyx


KV_CODE = '''
#:import defaults kivyx.uix.behaviors.tap.defaults

<Separator@Widget>:
    canvas:
        Color:
            rgb: 1, 0, 1
        Rectangle:
            pos: self.pos
            size: self.size
<VSep@Separator>:
    width: 3
    size_hint_x: None
<HSep@Separator>:
    height: 1
    size_hint_y: None

<MyGestureRecognizer@KXTapGestureRecognizer+Label>:

BoxLayout:
    BoxLayout:
        orientation: "vertical"
        spacing :4
        Label:
            text: "disabled"
            color: 0, 1, 0, 1
        Switch:
            id: disabled
        HSep:
        Label:
            text: "tap_disabled"
            color: 0, 1, 0, 1
        Switch:
            id: tap_disabled
        HSep:
        Label:
            text: "tap_track_multiple_touches"
            color: 0, 1, 0, 1
        Switch:
            id: tap_track_multiple_touches
            active: defaults.track_multiple_touches
    VSep:
    MyGestureRecognizer:
        text: "Tap me"
        font_size: "46sp"
        disabled: disabled.active
        tap_disabled: tap_disabled.active
        tap_track_multiple_touches: tap_track_multiple_touches.active
        on_tap: print(f"Tapped (touch.uid = {args[1].uid})")
'''


class SampleApp(App):
    def build(self):
        return Builder.load_string(KV_CODE)


if __name__ == "__main__":
    SampleApp(title="Tap Gensture Recognition Playground").run()
