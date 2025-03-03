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
    BoxLayout:
        orientation: "vertical"
        Label:
            text: "disabled"
            color: 0, 1, 0, 1
        Switch:
            id: disabled
        HSep:
        Label:
            text: f"track_width: {int(track_width.value)}"
            color: 0, 1, 0, 1
        Slider:
            id: track_width
            min: 32
            max: 256
            step: 1
            value: 128
        HSep:
        Label:
            text: f"track_height: {int(track_height.value)}"
            color: 0, 1, 0, 1
        Slider:
            id: track_height
            min: 32
            max: 256
            step: 1
            value: 64
        HSep:
        Label:
            text: f"anim_duration: {anim_duration.value:.1f}"
            color: 0, 1, 0, 1
        Slider:
            id: anim_duration
            min: 0.1
            max: 2.0
            step: 0.1
            value: 0.2
    VSep:
    KXSwitch:
        track_width: track_width.value
        track_height: track_height.value
        disabled: disabled.active
        anim_duration: anim_duration.value
'''


class SampleApp(App):
    def build(self):
        return Builder.load_string(KV_CODE)


if __name__ == '__main__':
    SampleApp(title="").run()
