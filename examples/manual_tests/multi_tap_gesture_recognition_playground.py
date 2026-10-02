from kivy.app import App
from kivy.lang import Builder
import asynckivy as ak
from kivy_garden import pyle

import kivyx


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
            text: "widget.disabled"
            color: 0, 1, 0, 1
        Switch:
            id: widget_disabled
        HSep:
        Label:
            text: "disabled"
            color: 0, 1, 0, 1
        Switch:
            id: disabled
        HSep:
        Label:
            text: f"max_count: {int(max_count.value)}"
            color: 0, 1, 0, 1
        Slider:
            id: max_count
            min: 1
            max: 7
            step: 1
            value: 2
        HSep:
        Label:
            text: f"max_time_interval: {max_time_interval.value:.2f}"
            color: 0, 1, 0, 1
        Slider:
            id: max_time_interval
            min: 0
            max: 2
            step: 0.01
            value: 0.3
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
        from kivyx.uix.behaviors.multitap import MultiTapGestureRecognizer

        rcg = MultiTapGestureRecognizer()
        rcg.bind(on_multi_tap=lambda *args: print(f"Multi-Tapped (touch.uids = {[t.uid for t in args[3]]})"))
        ids = self.root.ids
        target = ids.target

        @pyle.immediate_rule
        def update_max_count(_1, _2, max_count=ids.max_count.__self__, rcg=rcg):
            rcg.max_count = max(int(max_count.value), 1)
        with (
            ak.sync_attr((ids.widget_disabled, "active"), (target, "disabled"), eager=True),
            ak.sync_attr((ids.disabled, "active"), (rcg, "disabled"), eager=True),
            ak.sync_attr((ids.max_time_interval, "value"), (rcg, "max_time_interval"), eager=True),
            update_max_count,
        ):
            await rcg.enable_on(ids.target)


if __name__ == "__main__":
    SampleApp(title="Multi-Tap Gensture Recognition Playground").run()
