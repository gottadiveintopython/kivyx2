from kivy.app import App
from kivy.lang import Builder
import asynckivy as ak

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
            text: "track_multiple_touches"
            color: 0, 1, 0, 1
        Switch:
            id: track_multiple_touches
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
        from kivyx.uix.behaviors.tap import TapGestureRecognizer

        rcg = TapGestureRecognizer()
        rcg.bind(on_tap=lambda *args: print(f"Tapped (touch.uid = {args[2].uid})"))
        ids = self.root.ids
        target = ids.target
        with (
            ak.sync_attr((ids.widget_disabled, "active"), (target, "disabled"), eager=True),
            ak.sync_attr((ids.disabled, "active"), (rcg, "disabled"), eager=True),
            ak.sync_attr((ids.track_multiple_touches, "active"), (rcg, "track_multiple_touches"), eager=True),
        ):
            await rcg.enable_on(ids.target)


if __name__ == "__main__":
    SampleApp(title="TapGenstureRecognizer Playground").run()
