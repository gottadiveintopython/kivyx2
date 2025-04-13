from kivy.lang import Builder
from kivy.app import App
import kivyx

KV_CODE = '''
BoxLayout:
    padding: 40, 40
    spacing: 40
    orientation: 'vertical'
    KXMultiTapButton:
        font_size: 30
        text: "This recognizes multi-tap gestures."
        disabled: not switch.active
        tap_max_count: 7
        on_multi_tap: print(f"{args[1]}-tapped.")
    KXButton:
        font_size: 30
        text: "This one doesn't."
        disabled: not switch.active
        ripple_color: "#00FF0066"
        on_tap: print("tapped.")
    Switch:
        id: switch
        active: True
'''


class SampleApp(App):
    def build(self):
        return Builder.load_string(KV_CODE)


if __name__ == '__main__':
    SampleApp(title='multi-tap').run()
