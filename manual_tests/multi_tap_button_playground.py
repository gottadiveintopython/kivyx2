from kivy.app import App
from kivy.lang import Builder
import kivyx


KV_CODE = '''
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

BoxLayout:
    spacing: "10dp"
    padding: "10dp"
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
            text: f"tap_max_count: {int(tap_max_count.value)}"
            color: 0, 1, 0, 1
        Slider:
            id: tap_max_count
            min: 1
            max: 7
            step: 1
            value: 2
        HSep:
        Label:
            text: f"tap_max_interval: {tap_max_interval.value:.2f}"
            color: 0, 1, 0, 1
        Slider:
            id: tap_max_interval
            min: 0
            max: 2
            step: 0.01
            value: 0.3
    VSep:
    KXMultiTapButton:
        id: button
        tap_max_count: max(int(tap_max_count.value), 1)
        tap_max_interval: tap_max_interval.value
        disabled: disabled.active
        on_multi_tap: print(args[1], "- tapped.")
        font_size: "40sp"
        text: "TAP ME"
'''


class SampleApp(App):
    def build(self):
        return Builder.load_string(KV_CODE)


if __name__ == '__main__':
    SampleApp(title="MultiTapButton Playground").run()
