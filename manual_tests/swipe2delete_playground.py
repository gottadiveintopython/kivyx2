from kivy.app import App
from kivy.lang import Builder
from kivyx.uix.button import KXButton

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

<S2DBoxLayout@KXSwipe2DeleteBehavior+BoxLayout>:
    
BoxLayout:
    BoxLayout:
        orientation: "vertical"
        spacing :4
        Label:
            text: "disabled"
            color: 0, 1, 0, 1
        KXSwitch:
            id: disabled
        HSep:
        Label:
            text: "s2d_disabled"
            color: 0, 1, 0, 1
        KXSwitch:
            id: s2d_disabled
        HSep:
        Label:
            text: f"s2d_swipe_threshold: {int(s2d_swipe_threshold.value)}"
            color: 0, 1, 0, 1
        Slider:
            id: s2d_swipe_threshold
            min: 0
            max: dp(100)
            step: 1
            value: dp(20)
        HSep:
        Label:
            text: f"s2d_delete_threshold: {int(s2d_delete_threshold.value)}"
            color: 0, 1, 0, 1
        Slider:
            id: s2d_delete_threshold
            min: 0
            max: dp(500)
            step: 1
            value: dp(300)
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
            s2d_swipe_threshold: s2d_swipe_threshold.value
            s2d_delete_threshold: s2d_delete_threshold.value
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
