from kivy.app import App
from kivy.lang import Builder
import kivyx


KV_CODE = '''
#:import defaults kivyx.uix.behaviors.touchripple.defaults

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

<MyTouchRipple@KXTouchRippleBehavior+Label>:
<MyRelativeTouchRipple@KXTouchRippleBehavior+RelativeLayout>:

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
            text: "ripple_disabled"
            color: 0, 1, 0, 1
        Switch:
            id: ripple_disabled
        HSep:
        Label:
            text: "ripple_clip_to_bounds"
            color: 0, 1, 0, 1
        Switch:
            id: ripple_clip_to_bounds
            active: defaults.clip_to_bounds
        HSep:
        Label:
            text: f"ripple_initial_size: {int(ripple_initial_size.value)}"
            color: 0, 1, 0, 1
        Slider:
            id: ripple_initial_size
            min: 0
            max: 100
            step: 1
            value: defaults.initial_size
        HSep:
        Label:
            text: f"ripple_final_size: {int(ripple_final_size.value) if ripple_final_size_is_set.active else 'None'}"
            color: 0, 1, 0, 1
        Switch:
            id: ripple_final_size_is_set
            active: False
        Slider:
            id: ripple_final_size
            disabled: not ripple_final_size_is_set.active
            min: 0
            max: 400
            step: 1
            value: 0
        HSep:
        Label:
            text: "ripple_allow_multiple"
            color: 0, 1, 0, 1
        Switch:
            id: ripple_allow_multiple
            active: defaults.allow_multiple
    VSep:
    BoxLayout:
        orientation: "vertical"
        MyRelativeTouchRipple:
            disabled: disabled.active
            ripple_disabled: ripple_disabled.active
            ripple_allow_multiple: ripple_allow_multiple.active
            ripple_relative_coordinates: True
            ripple_clip_to_bounds: ripple_clip_to_bounds.active
            ripple_initial_size: ripple_initial_size.value
            ripple_final_size: ripple_final_size.value if ripple_final_size_is_set.active else None
            Label:
                text: "Touch Me\\n(RelativeLayout)"
                font_size: "46sp"
                halign: "center"
        HSep:
        MyTouchRipple:
            text: "Touch Me"
            font_size: "46sp"
            disabled: disabled.active
            ripple_disabled: ripple_disabled.active
            ripple_allow_multiple: ripple_allow_multiple.active
            ripple_relative_coordinates: False
            ripple_clip_to_bounds: ripple_clip_to_bounds.active
            ripple_initial_size: ripple_initial_size.value
            ripple_final_size: ripple_final_size.value if ripple_final_size_is_set.active else None
'''


class SampleApp(App):
    def build(self):
        return Builder.load_string(KV_CODE)


if __name__ == "__main__":
    SampleApp(title="Touch Ripple Effect Playground").run()
