from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.lang import Builder

from kivyx.uix.button import KXButton

class Numpad(GridLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        for text in "7 8 9 * 4 5 6 / 1 2 3 del 0 + - ent".split():
            self.add_widget(KXButton(
                text=text,
                size_hint=(None, None, ),
                size=(64, 64, ),
                font_size=24,
            ))


KV_CODE = r'''
<Numpad>:
    cols: 4
    rows: 4
    spacing: 10
    padding: 10
    size_hint: None, None
    size: self.minimum_size

FloatLayout:
    KXDrawer:
        size_hint: None, None
        size: numpad.size
        anchor: "lt"
        Numpad:
            id: numpad
    KXDrawer:
        size_hint: None, None
        anchor: "rt"
        KXButton:
            text: "A"
            font_size: 24
    KXDrawer:
        size_hint: None, None
        anchor: "rm"
        KXButton:
            text: "B"
            font_size: 24
    KXDrawer:
        size_hint_y: .2
        anchor: "bm"
        KXButton:
            text: "Hello Kivy"
            font_size: 24
'''


class SampleApp(App):
    def build(self):
        return Builder.load_string(KV_CODE)


if __name__ == '__main__':
    SampleApp().run()
