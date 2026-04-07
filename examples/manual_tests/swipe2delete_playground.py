from kivy.app import App
from kivy.lang import Builder
from kivyx.uix.button import KXButton

KV_CODE = '''
#:import defaults kivyx.uix.behaviors.swipe2delete.defaults

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

<S2DBoxLayout@KXSwipe2DeleteBehavior+BoxLayout>:
    
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
            text: "s2d_disabled"
            color: 0, 1, 0, 1
        Switch:
            id: s2d_disabled
        HSep:
        Label:
            text: "s2d_track_multiple_touches"
            color: 0, 1, 0, 1
        Switch:
            id: s2d_track_multiple_touches
        HSep:
        Label:
            text: f"s2d_swipe_distance: {int(s2d_swipe_distance.value)}"
            color: 0, 1, 0, 1
        Slider:
            id: s2d_swipe_distance
            min: 0
            max: dp(100)
            step: 1
            value: defaults.swipe_distance
        HSep:
        Label:
            text: f"s2d_delete_distance: {int(s2d_delete_distance.value)}"
            color: 0, 1, 0, 1
        Slider:
            id: s2d_delete_distance
            min: 0
            max: dp(500)
            step: 1
            value: defaults.delete_distance
        HSep:
        Label:
            text: f"s2d_direction: {'horizontal' if s2d_direction.active else 'vertical'}"
            color: 0, 1, 0, 1
        Switch:
            id: s2d_direction
            active: True
    VSep:
    KXScrollView:
        do_scroll_x: False
        S2DBoxLayout:
            id: container
            orientation: "vertical"
            size_hint_y: None
            height: self.minimum_height
            spacing: "10dp"
            padding: "10dp"
            disabled: disabled.active
            s2d_disabled: s2d_disabled.active
            s2d_swipe_distance: s2d_swipe_distance.value
            s2d_delete_distance: s2d_delete_distance.value
            s2d_track_multiple_touches: s2d_track_multiple_touches.active
            s2d_direction: "horizontal" if s2d_direction.active else "vertical"
'''


class SampleApp(App):
    def build(self):
        root = Builder.load_string(KV_CODE)

        def on_tap(btn, touch):
            print(btn.text, "tapped.")
        add_widget = root.ids.container.add_widget
        for i in range(20):
            add_widget(KXButton(text=str(i), font_size="30dp", size_hint_y=None, height="80dp", on_tap=on_tap))
        return root


if __name__ == '__main__':
    SampleApp(title="Swipe-to-Delete Playground").run()
