'''
https://youtu.be/4AHhps6GPbU
'''
from kivy.app import App
from kivy.lang import Builder
import asynckivy as ak

from kivyx.uix.button import KXButton
from kivyx.uix.behaviors.swipe2delete import enable_swipe2delete

KV_CODE = r'''
KXScrollView:
    do_scroll_x: False
    BoxLayout:
        id: container
        orientation: "vertical"
        size_hint_y: None
        height: self.minimum_height
        spacing: "10dp"
        padding: "10dp"
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

    def on_start(self):
        ak.managed_start(enable_swipe2delete(self.root.ids.container))


if __name__ == "__main__":
    SampleApp(title="Swipe-to-Delete").run()
