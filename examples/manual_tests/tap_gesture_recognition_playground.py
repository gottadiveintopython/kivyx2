import inspect

from kivy.app import App
from kivy.lang import Builder
import asynckivy as ak

from kivyx.uix.behaviors.tap import enable_tap_gesture_recognition


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

<Target@Label>:
    font_size: "96sp"
    size_hint: .6, .6
    canvas.after:
        Line:
            rectangle: [*self.pos, *self.size]

BoxLayout:
    BoxLayout:
        orientation: "vertical"
        size_hint_x: .5
        spacing :4
        Label:
            text: "consume_touch"
            color: 0, 1, 0, 1
        Switch:
            id: consume_touch
        HSep:
        Label:
            text: "track_multiple_touches"
            color: 0, 1, 0, 1
        Switch:
            id: track_multiple_touches
    VSep:
    FloatLayout:
        Target:
            id: bg_target
            text: "BG"
            pos_hint: {"x": 0.1, "y": 0.1}
            opacity: .3
        Target:
            id: fg_target
            text: "FG"
            pos_hint: {"right": 0.9, "top": 0.9}
'''


class SampleApp(App):
    def build(self):
        return Builder.load_string(KV_CODE)

    def on_start(self):
        ak.managed_start(self.main())

    async def main(self):
        reset_event = ak.Event()
        params = inspect.signature(enable_tap_gesture_recognition).parameters
        ids = self.root.ids
        for name in ["consume_touch", "track_multiple_touches"]:
            ids[name].active = params[name].default
            ids[name].bind(active=reset_event.fire)

        def on_tap(target, touch):
            print(f"{target.text} was tapped ({touch.uid = })")
        while True:
            await ak.sleep(0.2)
            async with ak.open_nursery() as nursery:
                s = nursery.start
                s(reset_event.wait(), close_on_finish=True)
                s(enable_tap_gesture_recognition(
                    ids.bg_target,
                    consume_touch=ids["consume_touch"].active,
                    track_multiple_touches=ids["track_multiple_touches"].active,
                    on_tap=on_tap,
                ))
                s(enable_tap_gesture_recognition(
                    ids.fg_target,
                    consume_touch=ids["consume_touch"].active,
                    track_multiple_touches=ids["track_multiple_touches"].active,
                    on_tap=on_tap,
                ))



if __name__ == "__main__":
    SampleApp(title="Tap Gensture Recognition Playground").run()
