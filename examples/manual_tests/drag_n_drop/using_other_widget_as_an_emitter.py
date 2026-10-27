from contextlib import ExitStack

from kivy.properties import ObjectProperty
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.label import Label
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Color, Rectangle, Line

import asynckivy as ak

import kivyx.uix.behaviors.drag_n_drop as dnd

KV_CODE = '''
#:import ascii_uppercase string.ascii_uppercase

<Cell>:
    canvas.before:
        Color:
            rgba: .1, .1, .1, 1
        Rectangle:
            pos: self.pos
            size: self.size

<Deck>:
    canvas.after:
        Color:
            rgba: 1, 1, 1, 1
        Line:
            rectangle: [*self.pos, *self.size, ]

BoxLayout:
    Widget:
        size_hint_x: .1

    # Place the board inside a RelativeLayout just to verify that the coordinates are correctly transformed.
    # This is not necessary for this example to work.
    RelativeLayout:
        GridLayout:
            id: board
            cols: 4
            rows: 4
            spacing: 10
            padding: 10

    BoxLayout:
        orientation: "vertical"
        size_hint_x: .2
        padding: "20dp", "40dp"
        spacing: "80dp"

        # Place a deck inside a RelativeLayout just to verify that the coordinates are correctly transformed.
        # This is not necessary for this example to work.
        RelativeLayout:
            Deck:
                board: board
                text: "numbers"
                font_size: "20sp"
                text_iter: (str(i) for i in range(10))
        Deck:
            board: board
            text: "letters"
            font_size: "20sp"
            text_iter: iter(ascii_uppercase)
'''


class Cell(FloatLayout):
    def on_kv_post(self, *args):
        super().on_kv_post(*args)
        ak.managed_start(dnd.enable_drop_target(self, on_drop=self.on_drop))

    @staticmethod
    def on_drop(self, touch, drag_cls, dragged_widget) -> bool:
        if self.children:
            return False
        self.add_widget(dragged_widget)
        return True


class Deck(Label):
    text_iter = None
    board = None

    def on_touch_down(self, touch):
        ox, oy = touch.opos
        if self.collide_point(ox, oy):
            if (text := next(self.text_iter, None)) is None:
                self.disabled = True
            else:
                card = Label(
                    size=self._get_cell_size(), center=self.to_window(ox, oy), pos_hint={"x": 0, "y": 0},
                    text=text, font_size=100,
                )
                ak.managed_start(dnd.perform_drag(card, touch))
            return True

    def _get_cell_size(self):
        return self.board.children[0].size


class SampleApp(App):
    def build(self):
        return Builder.load_string(KV_CODE)

    def on_start(self):
        board = self.root.ids.board
        for __ in range(board.cols * board.rows):
            board.add_widget(Cell())


if __name__ == "__main__":
    SampleApp(title="Using other widget as an emitter").run()
