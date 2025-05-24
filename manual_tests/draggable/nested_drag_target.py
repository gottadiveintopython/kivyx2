from kivy.app import App
from kivy.lang import Builder

import kivyx

KV_CODE = '''
<DragTarget@KXDragTargetBehavior+FloatLayout>:
    drag_classes: ["test", ]
    canvas.before:
        Color:
            rgba: 1, 1, 1, .5
        Line:
            rectangle: [*self.pos, *self.size]

<DraggableItem@KXDraggableBehavior+KXButton>:
    drag_cls: "test"
    drag_timeout: 0.1
    on_tap: print("tapped")

DragTarget:
    DragTarget:
        size_hint: .5, .5
        pos_hint: {'center_x': .5, 'center_y': .5, }
        DraggableItem:
            text: "A"
            font_size: 100
            size_hint: None, None
            size: 120, 120
            pos_hint: {'x': 0, 'y': 0, }
'''


class SampleApp(App):
    def build(self):
        return Builder.load_string(KV_CODE)


if __name__ == "__main__":
    SampleApp(title="Nested DragTarget").run()
