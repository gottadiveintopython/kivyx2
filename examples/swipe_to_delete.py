'''
https://youtu.be/4AHhps6GPbU
'''

from functools import partial

from kivy.metrics import dp
from kivy.app import App
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.graphics import Translate
import asynckivy as ak

from kivyx.touch_filters import is_opos_colliding
from kivyx.uix.button import KXButton


def remove_child(layout, child):
    layout.remove_widget(child)


async def enable_swipe_to_delete(target_layout, *, swipe_threshold=dp(10), delete_threshold=dp(300), delete_action=remove_child):
    '''
    Enables horizontal swipe-to-delete on a layout.

    :param swipe_threshold: The minimum distance a touch must travel to be recognized as a swipe.
    :param delete_threshold: The minimum distance a swipe must cover to trigger deletion.
    :param delete_action: The actual deletion behavior can be customized via this parameter.

    The effect of this function lasts until the coroutine is cancelled.
    '''
    abs_ = abs
    target = target_layout.__self__
    on_touch_down = partial(ak.event, target, "on_touch_down", filter=is_opos_colliding)
    while True:
        __, touch = await on_touch_down()
        # 'target.to_local()' here is not necessary for this example to work because the 'target' is an
        # instance of BoxLayout, and the BoxLayout is not a relative-type widget.
        ox, oy = target.to_local(*touch.opos)
        for c in target.children:
            if c.collide_point(ox, oy):
                break
        else:
            continue

        def is_the_same_touch(w, t, touch=touch):
            return t is touch
        ox, __ = target.to_window(*touch.opos)
        claim_signal = touch.ud["kivyx_claim_signal"]

        # Waits until the touch travels beyond the swipe threshold.
        async with (
            ak.move_on_when(claim_signal.wait()),
            ak.event_freq(Window, "on_touch_move", filter=is_the_same_touch) as on_touch_move,
        ):
            while True:
                await on_touch_move()
                if abs_(touch.x - ox) > swipe_threshold:
                    break

        if claim_signal.is_fired:
            continue  # Someone else claimed the touch, so we exit.
        claim_signal.fire()  # We claim the touch.

        try:
            fade_threshold = delete_threshold * 1.4
            orig_opacity = c.opacity
            # Moves and changes the opacity of the child during swipe.
            with ak.transform(c, use_outer_canvas=True) as ig:
                ig.add(translate := Translate())
                async with (
                    ak.move_on_when(touch.ud["kivyx_end_signal"].wait()),
                    ak.event_freq(Window, "on_touch_move", filter=is_the_same_touch) as on_touch_move,
                ):
                    while True:
                        await on_touch_move()
                        translate.x = diff = touch.x - ox
                        c.opacity = (1.0 - abs_(diff) / fade_threshold) * orig_opacity

            if abs_(diff) > delete_threshold:
                delete_action(target, c)
        finally:
            c.opacity = orig_opacity


KV_CODE = r'''
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
        root = Builder.load_string(KV_CODE)

        def on_tap(btn, __):
            print(btn.text, "tapped.")
        add_widget = root.ids.container.add_widget
        for i in range(20):
            add_widget(KXButton(text=str(i), font_size="30dp", size_hint_y=None, height="80dp", on_tap=on_tap))
        return root

    def on_start(self):
        ak.managed_start(enable_swipe_to_delete(self.root.ids.container))


if __name__ == "__main__":
    SampleApp(title="Swipe to Delete").run()
