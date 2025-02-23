from kivy.app import App
from kivy.lang import Builder
from kivy.factory import Factory as F
from kivy.clock import Clock
from random import randint
import kivyx

KV_CODE = r'''
<MyButton@KXTapGestureRecognizer+KXTouchRippleBehavior+Label>:
    font_size: 40
    size_hint_min: 300, 100
    on_tap: print(f"{self.text} tapped.")
    canvas.before:
        StencilPush:
        RoundedRectangle:
            pos: self.pos
            size: self.size
        StencilUse:
        Color:
            rgba: .4, .2, .8, 1
        Rectangle:
            pos: self.pos
            size: self.size
    canvas.after:
        StencilUnUse:
        RoundedRectangle:
            pos: self.pos
            size: self.size
        StencilPop:

KXScrollView:
    smooth_scroll_end: 50
    BoxLayout:
        id: container
        orientation: 'vertical'
        spacing: 10
        size_hint_y: None
        height: self.minimum_height
'''


class SampleApp(App):
    def build(self):
        return Builder.load_string(KV_CODE)

    def on_start(self):
        MyButton = F.MyButton
        add_widget = self.root.ids.container.add_widget
        for i in range(20):
            add_widget(MyButton(text=str(i)))

        def random_scroll(dt, sv=self.root):
            distance = randint(-500, 500)
            print("scroll by distance:", distance)
            sv.scroll_by_distance(None, distance)
        Clock.schedule_interval(random_scroll, 3)


if __name__ == '__main__':
    SampleApp().run()
