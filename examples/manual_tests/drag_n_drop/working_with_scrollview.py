from kivy.app import App
from kivy.lang import Builder
import asynckivy as ak
import kivyx

KV_CODE = '''
KXScrollView:
    do_scroll_x: False
    BoxLayout:
        id: container
        orientation: "vertical"
        spacing: 20
        padding: 20
        size_hint_y: None
        height: self.minimum_height
'''


class SampleApp(App):
    def build(self):
        return Builder.load_string(KV_CODE)

    def on_start(self):
        from kivyx.uix.button import KXButton
        import kivyx.uix.behaviors.drag_n_drop as dnd

        container = self.root.ids.container
        add_widget = container.add_widget
        default_bgcolor = KXButton.background_color.defaultvalue

        def on_tap(btn, touch):
            print(f"{btn.text} tapped")
        for i in range(20):
            add_widget(KXButton(text=str(i), size_hint_y=None, height=80, font_size=40, opacity=0.7, on_tap=on_tap))

        ak.managed_start(ak.wait_all(
            dnd.enable_drop_target_with_insertion_indicator(
                container,
                spacer_widgets=3,
            ),
            dnd.enable_drag_for_children(
                container,
                track_multiple_touches=True,
                on_start=lambda btn, *__: setattr(btn, "background_color", (1, .5, 0, 1)),
                on_end=lambda btn, *__: setattr(btn, "background_color", default_bgcolor),
            ),
        ))


if __name__ == "__main__":
    SampleApp(title="Working with ScrollView").run()
