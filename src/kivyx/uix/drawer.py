__all__ = ("KXDrawer", )

from functools import partial
from typing import TypeAlias, Literal
from contextlib import ExitStack

from kivy.metrics import sp as metrics_sp
from kivy.properties import NumericProperty, ColorProperty, OptionProperty
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget
import asynckivy as ak

from kivyx.uix.behaviors.tap import enable_tap_gesture_recognition


Anchor: TypeAlias = Literal["lt", "lm", "lb", "rt", "rm", "rb", "bl", "bm", "br", "tl", "tm", "tr"]

KV_CODE = '''
<KXDrawerTab>:
    canvas.before:
        Color:
            group: "bg_color"
        Rectangle:
            pos: self.pos
            size: self.size
    canvas:
        PushMatrix:
        Translate:
            xy: self.center
        Rotate:
            group: "icon_rotate"
        Color:
            group: "fg_color"
        Triangle:
            points: (s := min(*self.size) * 0.2, ) and (-s, -s, -s, s, s, 0.)
        PopMatrix:

<KXDrawer>:
    canvas.before:
        Color:
            rgba: root.bg_color
        Rectangle:
            pos: 0, 0
            size: self.size
    KXDrawerTab:
        id: tab
        anchor: root.anchor
        bg_color: root.bg_color
        fg_color: root.fg_color
'''
Builder.load_string(KV_CODE)


class KXDrawerTab(Widget):
    anchor: Anchor = OptionProperty("lm", options=Anchor.__args__)

    __ = {
        "l": {"x": 1., "center_y": .5, },
        "r": {"right": 0., "center_y": .5, },
        "b": {"y": 1., "center_x": .5, },
        "t": {"top": 0., "center_x": .5, },
    }
    @staticmethod
    def on_anchor(tab, anchor: Anchor, __=__):
        anchor = anchor[0]
        min_size = (max(metrics_sp(15), 24), ) * 2
        tab.size = tab.size_hint_min = min_size
        tab.size_hint = (.4, None) if anchor in "tb" else (None, .4)
        tab.pos_hint = __[anchor].copy()
    del __


class KXDrawer(RelativeLayout):
    '''
    A drawer widget that can be opened and closed by tapping on its tab or programmatically.
    '''
    __events__ = ("on_pre_open", "on_open", "on_pre_close", "on_close", )

    anim_duration = NumericProperty(.2)
    '''
    The time taken for the drawer to open and close.
    This does not include the time taken for the triangle on the tab to rotate, which is also ``anim_duration``.
    '''

    bg_color = ColorProperty("#222222")
    '''Background color'''

    fg_color = ColorProperty("#AAAAAA")
    '''Foreground color. Currently, it is only used for the color of the triangle on the tab.'''

    anchor: Anchor = OptionProperty("lm", options=Anchor.__args__)
    '''Where the drawer comes out from. '''

    def __init__(self, **kwargs):
        self._open_request = ak.StatefulEvent()
        self._close_request = ak.StatefulEvent()
        self._main_task = ak.dummy_task
        super().__init__(**kwargs)
        t = Clock.schedule_once(self._reset, -1)
        self.bind(parent=t, anchor=t, disabled=t, fg_color=t, bg_color=t)

    def _reset(self, dt):
        self._main_task.cancel()
        if self.parent is None or self.disabled:
            return
        self._main_task = ak.start(self._main())

    async def _main(self):
        import asynckivy as ak

        parent = self.parent
        if not isinstance(parent, FloatLayout):
            raise Exception("KXDrawer must belong to a FloatLayout (or a subclass).")

        open_request = self._open_request
        close_request = self._close_request
        tab = self.ids.tab.__self__
        anchor = self.anchor
        icon_rotate = tab.canvas.get_group("icon_rotate")[0]

        self.pos_hint = _get_fixed_part_of_pos_hint(anchor)
        # CAUTION: Kivyのプロパティへ等値を代入しようとすると実際には代入が行われない為、上の行と纏める事はできない。
        ph = self.pos_hint
        # '_c'-suffix means 'close'.  '_o'-suffix means 'open'.
        # For example: 'icon_angle_c' represents the icon angle when the drawer is closed.
        icon_angle_c = _get_initial_icon_angle(anchor)
        icon_angle_o = icon_angle_c + 180.
        pos_key_o, pos_key_c = _get_animated_pos_keys(anchor)
        ph_value = 0. if anchor[0] in "lb" else 1.
        icon_rotate.angle = icon_angle_c
        ph[pos_key_c] = ph_value
        get_parent_pos = partial(_get_parent_pos_in_local_coordinates, parent, pos_key_o, anchor[0] in "tb")

        # 三角が回っている時にanchorが特定の値から特定の値に変わった場合に必要となる。(例: 'tm' -> 'bm', 'tr' -> 'br')
        # 理由はpos_hintに変化が起きずlayoutの再計算を引き起こさないから。
        parent._trigger_layout()

        with ExitStack() as stack:
            stack.enter_context(ak.sync_attr(
                (self, "bg_color"),
                (tab.canvas.before.get_group("bg_color")[0], "rgba"),
            ))
            stack.enter_context(ak.sync_attr(
                (self, "fg_color"),
                (tab.canvas.get_group("fg_color")[0], "rgba"),
            ))
            on_tab_tap = ak.ExclusiveEvent()
            stack.callback(ak.start(enable_tap_gesture_recognition(
                tab, consume_touch=True, on_tap=on_tab_tap.fire,
            )).cancel)
            while True:
                await ak.wait_any(
                    open_request.wait(),
                    on_tab_tap.wait(),
                )
                open_request.clear()
                self.dispatch("on_pre_open")
                del ph[pos_key_c]
                await ak.anim_attrs(self, duration=self.anim_duration, **{pos_key_o: get_parent_pos()})
                await ak.anim_attrs(icon_rotate, duration=self.anim_duration, angle=icon_angle_o)
                ph[pos_key_o] = ph_value
                self.dispatch("on_open")
                await ak.wait_any(
                    close_request.wait(),
                    on_tab_tap.wait(),
                )
                close_request.clear()
                self.dispatch("on_pre_close")
                del ph[pos_key_o]
                await ak.anim_attrs(self, duration=self.anim_duration, **{pos_key_c: get_parent_pos()})
                await ak.anim_attrs(icon_rotate, duration=self.anim_duration, angle=icon_angle_c)
                ph[pos_key_c] = ph_value
                self.dispatch("on_close")

    def open(self, *_unused):
        '''Opens the drawer if it's closed'''
        self._close_request.clear()
        self._open_request.fire()

    def close(self, *_unused):
        '''Closes the drawer if it's open'''
        self._open_request.clear()
        self._close_request.fire()

    def on_pre_open(self): pass
    def on_open(self): pass
    def on_pre_close(self): pass
    def on_close(self): pass


def _get_parent_pos_in_local_coordinates(parent, pos_key, vertical: bool):
    return getattr(parent, pos_key) + parent.to_local(0, 0)[vertical]


__ = {
    "l": ("x", "right"),
    "t": ("top", "y"),
    "r": ("right", "x"),
    "b": ("y", "top"),
}
def _get_animated_pos_keys(anchor: Anchor, __=__):
    return __[anchor[0]]


__ = {
    "bl": {"x": 0., },
    "tl": {"x": 0., },
    "lb": {"y": 0., },
    "rb": {"y": 0., },
    "bm": {"center_x": .5, },
    "tm": {"center_x": .5, },
    "rm": {"center_y": .5, },
    "lm": {"center_y": .5, },
    "br": {"right": 1., },
    "tr": {"right": 1., },
    "lt": {"top": 1., },
    "rt": {"top": 1., },
}
def _get_fixed_part_of_pos_hint(anchor: Anchor, __=__):
    return __[anchor].copy()


__ = {"l": 0., "t": 270., "r": 180., "b": 90., }
def _get_initial_icon_angle(anchor, __=__):
    return __[anchor[0]]


del __
