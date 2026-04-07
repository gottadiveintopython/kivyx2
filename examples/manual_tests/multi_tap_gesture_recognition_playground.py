from kivy.app import App
from kivy.lang import Builder
import kivyx


KV_CODE = '''
#:import defaults kivyx.uix.behaviors.multitap.defaults

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

<MyGestureRecognizer@KXMultiTapGestureRecognizer+Label>:

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
            text: f"tap_max_count: {int(tap_max_count.value)}"
            color: 0, 1, 0, 1
        Slider:
            id: tap_max_count
            min: 1
            max: 7
            step: 1
            value: defaults.max_count
        HSep:
        Label:
            text: f"tap_max_time_interval: {tap_max_time_interval.value:.2f}"
            color: 0, 1, 0, 1
        Slider:
            id: tap_max_time_interval
            min: 0
            max: 2
            step: 0.01
            value: defaults.max_time_interval
    VSep:
    MyGestureRecognizer:
        on_multi_tap: print(f"Multi-Tapped (touch.uid = {[t.uid for t in args[2]]})")
        text: "Tap me"
        font_size: "46sp"
        disabled: disabled.active
        tap_disabled: tap_disabled.active
        tap_max_count: max(int(tap_max_count.value), 1)
        tap_max_time_interval: tap_max_time_interval.value
'''


class SampleApp(App):
    def build(self):
        return Builder.load_string(KV_CODE)


if __name__ == "__main__":
    SampleApp(title="Multi-Tap Gensture Recognition Playground").run()
