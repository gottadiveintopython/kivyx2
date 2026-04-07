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
            drag_classes: "A"
        VDivider:
        MyDropTarget:
            text: "A[size=40][color=ffffff]or[/color][/size]B"
            markup: True
            drag_classes: "AB"
        VDivider:
        MyDropTarget:
            text: "B"
            drag_classes: "B"
    HDivider:
    BoxLayout:
        id: initial_container
'''


class MyDropTarget(dnd.KXDropTargetBehavior, Label):
    n_ongoing_drags_inside = NumericProperty(0)

    def on_drag_enter(self, touch, drag_cls, dragged_widget):
        self.n_ongoing_drags_inside += 1
        print(f"{dragged_widget.text} entered {self.drag_classes}.")

    def on_drag_leave(self, touch, drag_cls, dragged_widget):
        self.n_ongoing_drags_inside -= 1
        print(f"{dragged_widget.text} left {self.drag_classes}.")

    def on_drop(self, touch, drag_cls, dragged_widget):
        print(f"{dragged_widget.text} dropped on {self.drag_classes}.")
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
            for drag_cls in "AB":
                for i in range(1, 5):
                    label = Label(text=f"{drag_cls}{i}", font_size=40)
                    add_widget(label)
                    nursery.start(dnd.enable_drag(label, drag_cls=drag_cls, triggers=(immediate, )))


if __name__ == "__main__":
    SampleApp().run()
