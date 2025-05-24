'''Alternative version of 'customizing_animation.py'. This one adds graphics instructions on demand,
requires less bindings, thus probably more efficient than the original.
'''

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.graphics import Rotate, Scale

import asynckivy as ak

from kivyx.uix.behaviors.draggable import KXDragTargetBehavior, KXDraggableBehavior

KV_CODE = '''
<Cell>:
    drag_classes: ["test", ]
    canvas.before:
        Color:
            rgba: .1, .1, .1, 1
        Rectangle:
            pos: self.pos
            size: self.size

<DraggableItem>:
    drag_cls: "test"
    drag_timeout: 0
    font_size: 50
    pos_hint: {"x": 0, "y": 0, }
    canvas.before:
        Color:
            rgba: .4, 1, .2, 1 if self.is_being_dragged else 0
        Line:
            width: 2
            rectangle: [*self.pos, *self.size, ]

GridLayout:
    id: board
    cols: 3
    rows: 3
    spacing: 20
    padding: 20
'''


class DraggableItem(KXDraggableBehavior, Label):
    async def on_drag_fail(self, touch, ctx):
        with ak.transform(self) as ig:
            ig.add(rotate := Rotate(origin=self.center))
            async for p in ak.anim_with_ratio(base=.4):
                if p > 1.:
                    break
                rotate.angle = p * 720.
                self.opacity = 1. - p
            self.parent.remove_widget(self)

    async def on_drag_succeed(self, touch, ctx):
        await ak.sleep(0)  # wait for the layout to complete
        abs_ = abs
        with ak.transform(self) as ig:
            ig.add(scale := Scale(origin=self.center))
            async for p in ak.anim_with_ratio(base=.2):
                if p > 1.:
                    break
                scale.x = scale.y = abs_(p * .8 - .4) + .6


class Cell(KXDragTargetBehavior, FloatLayout):
    def on_drag_release(self, touch, ctx) -> bool:
        if self.children:
            return False
        return super().on_drag_release(touch, ctx)


class SampleApp(App):
    def build(self):
        return Builder.load_string(KV_CODE)

    def on_start(self):
        board = self.root
        for __ in range(board.cols * board.rows):
            board.add_widget(Cell())
        cells = board.children
        for cell, i in zip(cells, range(4)):
            cell.add_widget(DraggableItem(text=str(i)))


if __name__ == "__main__":
    SampleApp(title="Customizing animations").run()
