'''
This example shows how to achieve the same functionality as Flutter one's
'child', 'feedback' and 'childWhenDragging'.
https://api.flutter.dev/flutter/widgets/Draggable-class.html
'''

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.relativelayout import RelativeLayout

from kivyx import gesture_detectors
from kivyx.uix.behaviors.drag_n_drop import KXDropTargetBehavior, KXDraggableBehavior

KV_CODE = '''
<Cell>:
    canvas.before:
        Color:
            rgba: .1, .1, .1, 1
        Rectangle:
            size: self.size

<FlutterStyleDraggable>:
    Label:
        id: child
        text: "child"
        bold: True
    Label:
        id: childWhenDragging
        text: "childWhenDragging"
        bold: True
        color: 1, 0, 1, 1
    Label:
        id: feedback
        text: "feedback"
        bold: True
        color: 1, 1, 0, 1

GridLayout:
    id: board
    cols: 4
    rows: 4
    spacing: 10
    padding: 10
'''

class FlutterStyleDraggable(KXDraggableBehavior, RelativeLayout):
    def on_kv_post(self, *args, **kwargs):
        super().on_kv_post(*args, **kwargs)
        self._widgets = ws = {
            name: self.ids[name].__self__
            for name in ("child", "childWhenDragging", "feedback", )
        }
        self.remove_widget(ws["childWhenDragging"])
        self.remove_widget(ws["feedback"])
        self.drag_triggers = (gesture_detectors.immediate, )

    def on_drag_start(self, touch, drag_cls):
        ws = self._widgets
        self.remove_widget(ws['child'])
        self.add_widget(ws['feedback'])
        self.parent.add_widget(ws['childWhenDragging'])
        return super().on_drag_start(touch, drag_cls)

    def on_drag_end(self, touch, drag_cls, drag_result):
        ws = self._widgets
        w = ws['childWhenDragging']
        w.parent.remove_widget(w)
        self.remove_widget(ws['feedback'])
        self.add_widget(ws['child'])
        return super().on_drag_end(touch, drag_cls, drag_result)


class Cell(KXDropTargetBehavior, RelativeLayout):
    def on_drop(self, touch, drag_cls, dragged_widget) -> bool:
        if self.children:
            return False
        return super().on_drop(touch, drag_cls, dragged_widget)


class SampleApp(App):
    def build(self):
        return Builder.load_string(KV_CODE)

    def on_start(self):
        board = self.root
        for __ in range(board.cols * board.rows):
            board.add_widget(Cell())
        cells = board.children
        for cell, __ in zip(cells, range(4)):
            cell.add_widget(FlutterStyleDraggable())


if __name__ == "__main__":
    SampleApp(title="Flutter style Draggable").run()
