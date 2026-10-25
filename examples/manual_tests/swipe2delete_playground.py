import inspect

from kivy.app import App
from kivy.lang import Builder
from kivyx.uix.button import KXButton
import asynckivy as ak

from kivyx.uix.behaviors.swipe2delete import enable_swipe2delete_for_children

KV_CODE = '''
<Separator@Widget>:
    canvas:
        Color:
            rgb: 1, 0, 1
        Rectangle:
            pos: self.pos
            size: self.size
<VSep@Separator>:
    width: 3
    size_hint_x: None
<HSep@Separator>:
    height: 1
    size_hint_y: None

BoxLayout:
    BoxLayout:
        orientation: "vertical"
        spacing :4
        Label:
            text: "track_multiple_touches"
            color: 0, 1, 0, 1
        Switch:
            id: track_multiple_touches
        HSep:
        Label:
            text: f"swipe_distance: {int(swipe_distance.value)}"
            color: 0, 1, 0, 1
        Slider:
            id: swipe_distance
            min: 0
            max: dp(100)
            step: 1
        HSep:
        Label:
            text: f"delete_distance: {int(delete_distance.value)}"
            color: 0, 1, 0, 1
        Slider:
            id: delete_distance
            min: 0
            max: dp(500)
            step: 1
        HSep:
        Label:
            text: f"direction: {'horizontal' if direction.active else 'vertical'}"
            color: 0, 1, 0, 1
        Switch:
            id: direction
            active: True
    VSep:
    KXScrollView:
        do_scroll_x: False
        BoxLayout:
            id: container
            orientation: "vertical"
            size_hint_y: None
            height: self.minimum_height
            spacing: "10dp"
            padding: "10dp"
'''


class SampleApp(App):
    def build(self):
        def on_tap(btn, touch):
            print(btn.text, "tapped.")
        root = Builder.load_string(KV_CODE)
        add_widget = root.ids.container.add_widget
        for i in range(20):
            add_widget(KXButton(text=str(i), font_size="30dp", size_hint_y=None, height="80dp", on_tap=on_tap))
        return root

    def on_start(self):
        ak.managed_start(self.main())

    async def main(self):
        reset_event = ak.Event()
        params = inspect.signature(enable_swipe2delete_for_children).parameters
        ids = self.root.ids
        for name in ["swipe_distance", "delete_distance", ]:
            ids[name].value = params[name].default
            ids[name].bind(value=reset_event.fire)
        for name in ["track_multiple_touches", ]:
            ids[name].active = params[name].default
            ids[name].bind(active=reset_event.fire)
        ids["direction"].active = params["direction"].default == "horizontal"
        ids["direction"].bind(active=reset_event.fire)

        while True:
            await ak.sleep(0.2)
            async with ak.open_nursery() as nursery:
                s = nursery.start
                s(reset_event.wait(), close_on_finish=True)
                s(enable_swipe2delete_for_children(
                    ids.container,
                    swipe_distance=ids["swipe_distance"].value,
                    delete_distance=ids["delete_distance"].value,
                    track_multiple_touches=ids["track_multiple_touches"].active,
                    direction="horizontal" if ids["direction"].active else "vertical",
                ))


if __name__ == "__main__":
    SampleApp(title="Swipe-to-Delete Playground").run()
