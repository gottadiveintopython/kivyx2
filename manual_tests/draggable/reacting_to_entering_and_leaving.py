from kivy.properties import NumericProperty
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.label import Label
import asynckivy as ak

from kivyx.uix.behaviors.draggable import KXDraggableBehavior, KXDragTargetBehavior

KV_CODE = '''
<MyDragTarget>:
    text: "".join(root.drag_classes)
    font_size: 100
    color: 1, .2, 1, .8
    canvas.before:
        Color:
            rgba: 1, 1, 1, self.n_ongoing_drags_inside * 0.12
        Rectangle:
            pos: self.pos
            size: self.size

<MyDraggable>:
    drag_timeout: 0
    font_size: 40
    opacity: .3 if root.is_being_dragged else 1.

<Divider@Widget>:
    canvas:
        Color:
            rgb: 1, 1, 1
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
        MyDragTarget:
            drag_classes: ["A", ]
        VDivider:
        MyDragTarget:
            drag_classes: ["A", "B", ]
        VDivider:
        MyDragTarget:
            drag_classes: ["B", ]
    HDivider:
    BoxLayout:
        MyDraggable:
            drag_cls: "A"
            text: "A1"
        MyDraggable:
            drag_cls: "A"
            text: "A2"
        MyDraggable:
            drag_cls: "A"
            text: "A3"
        MyDraggable:
            drag_cls: "A"
            text: "A4"
        MyDraggable:
            drag_cls: "B"
            text: "B1"
        MyDraggable:
            drag_cls: "B"
            text: "B2"
        MyDraggable:
            drag_cls: "B"
            text: "B3"
        MyDraggable:
            drag_cls: "B"
            text: "B4"
'''


class MyDraggable(KXDraggableBehavior, Label):
    def on_drag_succeed(self, touch, ctx):
        self.parent.remove_widget(self)


class MyDragTarget(KXDragTargetBehavior, Label):
    n_ongoing_drags_inside = NumericProperty(0)

    def on_drag_enter(self, touch, ctx):
        self.n_ongoing_drags_inside += 1
        print(f"{ctx.draggable.text} entered {self.text}.")

    def on_drag_leave(self, touch, ctx):
        self.n_ongoing_drags_inside -= 1
        print(f"{ctx.draggable.text} left {self.text}.")


class SampleApp(App):
    def build(self):
        return Builder.load_string(KV_CODE)


if __name__ == '__main__':
    SampleApp().run()
