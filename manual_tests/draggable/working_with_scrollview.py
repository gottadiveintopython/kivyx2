'''
Nothing special. Just an example of re-orderable BoxLayout.
'''

from kivy.app import App
from kivy.lang import Builder
from kivy.factory import Factory
import kivyx

KV_CODE = '''
#:import Label kivy.uix.label.Label

<DraggableItem@KXDraggableBehavior+KXButton>:
    drag_cls: 'test'
    opacity: .5 if self.is_being_dragged else 1.
    background_color: (.8, .2, .2, 1) if self.is_being_dragged else (.4, .2, .8, 1)
    size_hint_min_y: sp(50)
    on_tap: print(self.text, "tapped")

<ReorderableBoxLayout@KXDragReorderBehavior+BoxLayout>:

KXScrollView:
    do_scroll_x: False
    ReorderableBoxLayout:
        id: boxlayout
        spacing: 2
        drag_classes: ["test", ]
        spacer_widgets:
            [
            Label(text="spacer #3", font_size=40, size_hint_min_y="50sp"),
            Label(text="spacer #2", font_size=40, size_hint_min_y="50sp"),
            Label(text="spacer #1", font_size=40, size_hint_min_y="50sp"),
            ]
        orientation: "vertical"
        padding: 10
        size_hint_min_y: self.minimum_height
'''


class SampleApp(App):
    def build(self):
        return Builder.load_string(KV_CODE)

    def on_start(self):
        DraggableItem = Factory.DraggableItem
        add_widget = self.root.ids.boxlayout.add_widget
        for i in range(100):
            add_widget(DraggableItem(text=str(i)))


if __name__ == "__main__":
    SampleApp(title="Working with ScrollView").run()
