from kivy.config import Config
# Config.set('modules', 'touchring', '')
Config.set('graphics', 'width', '1280')
Config.set('graphics', 'height', '720')
# Config.set('graphics', 'fullscreen', 1)
from kivy.app import App
from kivy.properties import ObjectProperty, StringProperty
from kivy.lang import Builder
from kivy.factory import Factory as F
from kivy.uix.boxlayout import BoxLayout
import kivyx


KV_CODE = '''
<MyButton@KXButton>:
    font_size: 60
    size_hint_min: 300, 150
    on_tap: print(f"{self.text} was tapped.")

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

<ScrollViewConfigurator>:
    orientation: 'vertical'
    Label:
        text: root.name
        font_size: 20
        bold: True
        color: 1, 1, 1, 1
        halign: 'center'
    HSep:
    Label:
        text: 'disabled'
        color: 0, 1, 0, 1
    Switch:
        id: disabled
    HSep:
    Label:
        text: 'do_scroll_x'
        color: 0, 1, 0, 1
    Switch:
        id: do_scroll_x
    HSep:
    Label:
        text: 'do_overscroll_x'
        color: 0, 1, 0, 1
    Switch:
        id: do_overscroll_x
    HSep:
    Label:
        text: 'do_scroll_y'
        color: 0, 1, 0, 1
    Switch:
        id: do_scroll_y
    HSep:
    Label:
        text: 'do_overscroll_y'
        color: 0, 1, 0, 1
    Switch:
        id: do_overscroll_y
    HSep:
    Label:
        text: 'hbar_enabled'
        color: 0, 1, 0, 1
    Switch:
        id: hbar_enabled
    HSep:
    Label:
        text: 'vbar_enabled'
        color: 0, 1, 0, 1
    Switch:
        id: vbar_enabled

BoxLayout:
    padding: 10
    spacing: 10
    ScrollViewConfigurator:
        name: "Outer\\nScrollView"
        sv: outer_sv
        size_hint_x: .2
        size_hint_min_x: 200
    VSep:
    ScrollViewConfigurator:
        name: "Inner\\nScrollView"
        sv: inner_sv
        size_hint_x: .2
        size_hint_min_x: 200
    VSep:
    KXScrollView:
        id: outer_sv
        smooth_scroll_end: 100
        BoxLayout:
            orientation: 'vertical'
            spacing: 10
            size_hint_y: None
            height: self.minimum_height
            MyButton:
                text: "A"
            MyButton:
                text: "B"
            MyButton:
                text: "C"
            KXScrollView:
                id: inner_sv
                smooth_scroll_end: 100
                size_hint_y: None
                height: 300
                GridLayout:
                    id: grid
                    cols: 4
                    spacing: 10
                    size_hint: None, None
                    size: self.minimum_size
            MyButton:
                text: "D"
            MyButton:
                text: "E"
'''


class ScrollViewConfigurator(BoxLayout):
    sv = ObjectProperty()
    name = StringProperty()
    TARGET_PROPERTIES = (
        "disabled", "do_scroll_x", "do_scroll_y", "do_overscroll_x", "do_overscroll_y",
        "hbar_enabled", "vbar_enabled",
    )

    def on_kv_post(self, *args):
        ids = self.ids
        sv = self.sv
        for prop in self.TARGET_PROPERTIES:
            setattr(ids[prop], "active", getattr(sv, prop))
            ids[prop].fbind("active", sv.setter(prop))


class SampleApp(App):
    def build(self):
        return Builder.load_string(KV_CODE)

    def on_start(self):
        MyButton = F.MyButton
        add_widget = self.root.ids.grid.add_widget
        for i in range(21):
            add_widget(MyButton(text=str(i)))


if __name__ == '__main__':
    SampleApp(title="ScrollView Playground").run()
