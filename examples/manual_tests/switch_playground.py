from kivy.app import App
from kivy.lang import Builder
import kivyx


KV_CODE = '''
#:import SW kivyx.uix.switch.KXSwitch

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
        spacing :4
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
            max: 512
            step: 1
            value: SW.track_width.defaultvalue
        HSep:
        Label:
            text: f"track_height: {int(track_height.value)}"
            color: 0, 1, 0, 1
        Slider:
            id: track_height
            min: 32
            max: 256
            step: 1
            value: SW.track_height.defaultvalue
        HSep:
        Button:
            text: "switch.active = True"
            on_press: switch.active = True
        Button:
            text: "switch.active = False"
            on_press: switch.active = False
    VSep:
    KXSwitch:
        id: switch
        track_width: track_width.value
        track_height: track_height.value
        disabled: disabled.active
        size_hint_min: self.minimum_size
'''


class SampleApp(App):
    def build(self):
        return Builder.load_string(KV_CODE)


if __name__ == '__main__':
    SampleApp(title="Switch Playground").run()
