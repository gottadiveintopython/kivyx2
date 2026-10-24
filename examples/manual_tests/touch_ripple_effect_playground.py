import inspect

from kivy.app import App
from kivy.lang import Builder
import asynckivy as ak

from kivyx.uix.behaviors.touchripple import enable_touch_ripple_effect, OptionalParams


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
            text: "clip_to_bounds"
            color: 0, 1, 0, 1
        Switch:
            id: clip_to_bounds
        HSep:
        Label:
            text: f"initial_size: {int(initial_size.value)}"
            color: 0, 1, 0, 1
        Slider:
            id: initial_size
            min: 0
            max: 100
            step: 1
        HSep:
        Label:
            text: f"growth_duration: {growth_duration.value:.01f}"
            color: 0, 1, 0, 1
        Slider:
            id: growth_duration
            min: 0.1
            max: 2
            step: 0.1
        HSep:
        Label:
            text: f"fadeout_duration: {fadeout_duration.value:.01f}"
            color: 0, 1, 0, 1
        Slider:
            id: fadeout_duration
            min: 0.1
            max: 2
            step: 0.1
        HSep:
        Label:
            text: f"final_size: {int(final_size.value) if final_size_is_set.active else 'None'}"
            color: 0, 1, 0, 1
        Switch:
            id: final_size_is_set
            active: False
        Slider:
            id: final_size
            disabled: not final_size_is_set.active
            min: 0
            max: 400
            step: 1
            value: 0
        HSep:
        Label:
            text: "allow_multiple"
            color: 0, 1, 0, 1
        Switch:
            id: allow_multiple
    VSep:
    BoxLayout:
        orientation: "vertical"
        RelativeLayout:
            id: relative_target
            Label:
                text: "Touch Me\\n(RelativeLayout)"
                font_size: "46sp"
                halign: "center"
        HSep:
        Label:
            id: target
            text: "Touch Me"
            font_size: "46sp"
'''


class SampleApp(App):
    def build(self):
        return Builder.load_string(KV_CODE)

    def on_start(self):
        ak.managed_start(self.main())

    async def main(self):
        reset_event = ak.Event()
        params = inspect.signature(enable_touch_ripple_effect).parameters
        ids = self.root.ids
        for name in ("clip_to_bounds", "allow_multiple"):
            ids[name].active = params[name].default
            ids[name].bind(active=reset_event.fire)
        for name in ("initial_size", "growth_duration", "fadeout_duration"):
            ids[name].value = params[name].default
            ids[name].bind(value=reset_event.fire)
        v = params["final_size"].default
        ids["final_size_is_set"].active = v is not None
        if v is not None:
            ids["final_size"].value = v
        ids["final_size"].bind(value=reset_event.fire)
        ids["final_size_is_set"].bind(active=reset_event.fire)

        while True:
            await ak.sleep(0.2)
            async with ak.open_nursery() as nursery:
                s = nursery.start
                s(reset_event.wait(), close_on_finish=True)
                params = OptionalParams(
                    clip_to_bounds=ids["clip_to_bounds"].active,
                    allow_multiple=ids["allow_multiple"].active,
                    initial_size=ids["initial_size"].value,
                    growth_duration=ids["growth_duration"].value,
                    fadeout_duration=ids["fadeout_duration"].value,
                    final_size=ids["final_size"].value if ids["final_size_is_set"].active else None,
                )
                s(enable_touch_ripple_effect(ids.target, **params))
                s(enable_touch_ripple_effect(ids.relative_target, relative_coordinates=True, **params))


if __name__ == "__main__":
    SampleApp(title="Touch Ripple Effect Playground").run()
