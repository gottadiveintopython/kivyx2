from kivy.properties import NumericProperty
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.label import Label
import asynckivy as ak

from kivyx.uix.behaviors import drag_n_drop as dnd

KV_CODE = '''
<MyDropTarget>:
    font_size: 100
    color: 1, .2, 1, .8
    canvas.before:
        Color:
            rgba: 1, 1, 1, self.n_ongoing_drags_inside * 0.12
        Rectangle:
            pos: self.pos
            size: self.size

<Divider@Widget>:
    canvas:
        Color:
        Rectangle:
            pos: self.pos
            size: self.size
<HDivider@Divider>:
    size_hint_y: None
    height: 1
<VDivider@Divider>:
    size_hint_x: None
    width: 1

BoxLayout:
    orientation: "vertical"
    BoxLayout:
        MyDropTarget:
            text: "A"
            drop_tags: {"A"}
        VDivider:
        MyDropTarget:
            text: "A[size=40][color=ffffff]or[/color][/size]B"
            markup: True
            drop_tags: {"A", "B"}
        VDivider:
        MyDropTarget:
            text: "B"
            drop_tags: {"B"}
    HDivider:
    BoxLayout:
        id: initial_container
'''


class MyDropTarget(Label):
    drop_tags = set()
    n_ongoing_drags_inside = NumericProperty(0)

    def on_kv_post(self, *args):
        super().on_kv_post(*args)
        ak.managed_start(dnd.enable_drop_target(
            self,
            drop_tags=self.drop_tags,
            on_enter=self.on_drag_enter,
            on_leave=self.on_drag_leave,
            on_drop=self.on_drop,
        ))

    @staticmethod
    def on_drag_enter(self, touch, drag_tags, dragged_widget):
        self.n_ongoing_drags_inside += 1
        print(f"{dragged_widget.text} entered {self.drop_tags}.")

    @staticmethod
    def on_drag_leave(self, touch, drag_tags, dragged_widget):
        self.n_ongoing_drags_inside -= 1
        print(f"{dragged_widget.text} left {self.drop_tags}.")

    @staticmethod
    def on_drop(self, touch, drag_tags, dragged_widget):
        print(f"{dragged_widget.text} dropped on {self.drop_tags}.")
        return True


class SampleApp(App):
    def build(self):
        return Builder.load_string(KV_CODE)

    def on_start(self):
        ak.managed_start(self.main())

    async def main(self):
        from kivyx.gesture_detectors import immediate
        add_widget = self.root.ids.initial_container.add_widget
        async with ak.open_nursery() as nursery:
            for drag_tags in "AB":
                for i in range(1, 5):
                    label = Label(text=f"{drag_tags}{i}", font_size=40)
                    add_widget(label)
                    nursery.start(dnd.enable_drag(label, drag_tags=drag_tags, triggers=(immediate, )))


if __name__ == "__main__":
    SampleApp().run()
