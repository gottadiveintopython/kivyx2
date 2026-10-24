import inspect

from kivy.app import App
from kivy.lang import Builder
import asynckivy as ak

from kivyx.uix.behaviors.multitap import enable_multi_tap_gesture_recognition


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
            text: f"max_count: {int(max_count.value)}"
            color: 0, 1, 0, 1
        Slider:
            id: max_count
            min: 1
            max: 7
            step: 1
        HSep:
        Label:
            text: f"max_time_interval: {max_time_interval.value:.2f}"
            color: 0, 1, 0, 1
        Slider:
            id: max_time_interval
            min: 0
            max: 2
            step: 0.01
    VSep:
    Label:
        id: target
        text: "Tap me"
        font_size: "46sp"
'''


class SampleApp(App):
    def build(self):
        return Builder.load_string(KV_CODE)

    def on_start(self):
        ak.managed_start(self.main())

    async def main(self):
        reset_event = ak.Event()
        params = inspect.signature(enable_multi_tap_gesture_recognition).parameters
        ids = self.root.ids
        for name in ["max_count", "max_time_interval"]:
            ids[name].value = params[name].default
            ids[name].bind(value=reset_event.fire)

        def on_multi_tap(target, n_taps, touches):
            print(f"Multi-Tapped (touch.uids = {[t.uid for t in touches]})")
        while True:
            await ak.sleep(0.2)
            async with ak.open_nursery() as nursery:
                s = nursery.start
                s(reset_event.wait(), close_on_finish=True)
                s(enable_multi_tap_gesture_recognition(
                    ids.target,
                    max_count=ids["max_count"].value,
                    max_time_interval=ids["max_time_interval"].value,
                    on_multi_tap=on_multi_tap,
                ))


if __name__ == "__main__":
    SampleApp(title="Multi-Tap Gensture Recognition Playground").run()
