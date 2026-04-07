from kivy.app import App
from kivy.lang import Builder
import asynckivy as ak
import kivyx

KV_CODE = '''
FloatLayout:
    FloatLayout:
        id: inner_drop_target
        size_hint: .5, .5
        pos_hint: {'center_x': .5, 'center_y': .5, }
        canvas.before:
            Color:
                rgba: 1, 1, 1, .5
            Line:
                rectangle: [*self.pos, *self.size]
        KXButton:
            id: btn
            text: "A"
            font_size: 100
            size_hint: None, None
            size: 120, 120
            pos_hint: {'x': 0, 'y': 0, }
            on_tap: print("tapped")
'''


class SampleApp(App):
    def build(self):
        return Builder.load_string(KV_CODE)

    def on_start(self):
        import kivyx.uix.behaviors.drag_n_drop as dnd
        from kivyx.gesture_detectors import direction_free_swipe

        outer_drop_target = self.root
        inner_drop_target = self.root.ids.inner_drop_target
        btn = self.root.ids.btn
        ak.managed_start(ak.wait_all(
            dnd.enable_drop_target(outer_drop_target),
            dnd.enable_drop_target(inner_drop_target),
            dnd.enable_drag(btn, triggers=(direction_free_swipe, )),
        ))


if __name__ == "__main__":
    SampleApp(title="Nested Drop Target").run()
