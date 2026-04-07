'''
https://www.youtube.com/watch?v=PNj8uEdd5c0

To animate widgets like in the video: $ pip install kivy-garden-posani
'''

from collections.abc import Iterable
import itertools
from contextlib import closing
from os import PathLike
import sqlite3
from dataclasses import dataclass

from kivy.app import App
from kivy.properties import ObjectProperty
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.factory import Factory as F
import asynckivy as ak
from asynckivy import modal

try:
    from kivy_garden import posani
except ImportError:
    pass
else:
    posani.install(target="SHFood")


def detect_image_format(image_data: bytes) -> str:
    if image_data.startswith(b"\x89\x50\x4E\x47\x0D\x0A\x1A\x0A"):
        return "png"
    elif image_data.startswith(b"\xFF\xD8"):
        return "jpg"
    raise ValueError("Unknown image format")


def _reload_texture(BytesIO, CoreImage, image_data: bytes, image_type: str, texture):
    # NOTE: This function is untested because I don't know how to trigger an OpenGL context loss.
    # https://kivy.org/doc/master/api-kivy.graphics.texture.html#reloading-the-texture
    img = CoreImage(BytesIO(image_data), ext=image_type)
    texture.blit_data(img._image._data[0])


def load_database(db_path: PathLike) -> list["Food"]:
    from functools import partial
    from io import BytesIO
    from kivy.core.image import Image as CoreImage

    with sqlite3.connect(str(db_path)) as conn:
        reload_texture = partial(_reload_texture, BytesIO, CoreImage)
        return [
            (
                tex := CoreImage(BytesIO(image_data), ext=image_type).texture,
                tex.add_reload_observer(partial(reload_texture, image_data, image_type)),
            ) and Food(name=name, price=price, texture=tex)
            for name, price, image_data, image_type in conn.execute("SELECT name, price, image, image_type FROM Foods")
        ]


def init_database(db_path: PathLike):
    import requests

    FOOD_DATA = (
        # (name, price, image_url)
        ("blueberry", 500, r"https://3.bp.blogspot.com/-RVk4JCU_K2M/UvTd-IhzTvI/AAAAAAAAdhY/VMzFjXNoRi8/s180-c/fruit_blueberry.png"),
        ("cacao", 800, r"https://3.bp.blogspot.com/-WT_RsvpvAhc/VPQT6ngLlmI/AAAAAAAAsEA/aDIU_F9TYc8/s180-c/fruit_cacao_kakao.png"),
        ("dragon fruit", 1200, r"https://1.bp.blogspot.com/-hATAhM4UmCY/VGLLK4mVWYI/AAAAAAAAou4/-sW2fvsEnN0/s180-c/fruit_dragonfruit.png"),
        ("kiwi", 130, r"https://2.bp.blogspot.com/-Y8xgv2nvwEs/WCdtGij7aTI/AAAAAAAA_fo/PBXfb8zCiQAZ8rRMx-DNclQvOHBbQkQEwCLcB/s180-c/fruit_kiwi_green.png"),
        ("lemon", 200, r"https://2.bp.blogspot.com/-UqVL2dBOyMc/WxvKDt8MQbI/AAAAAAABMmk/qHrz-vwCKo8okZsZpZVDsHLsKFXdI1BjgCLcBGAs/s180-c/fruit_lemon_tategiri.png"),
        ("mangosteen", 300, r"https://4.bp.blogspot.com/-tc72dGzUpww/WGYjEAwIauI/AAAAAAABAv8/xKvtWmqeKFcro6otVdLi5FFF7EoVxXiEwCLcB/s180-c/fruit_mangosteen.png"),
        ("apple", 150, r"https://4.bp.blogspot.com/-uY6ko43-ABE/VD3RiIglszI/AAAAAAAAoEA/kI39usefO44/s180-c/fruit_ringo.png"),
        ("orange", 100, r"https://1.bp.blogspot.com/-fCrHtwXvM6w/Vq89A_TvuzI/AAAAAAAA3kE/fLOFjPDSRn8/s180-c/fruit_slice10_orange.png"),
        ("soldum", 400, r"https://2.bp.blogspot.com/-FtWOiJkueNA/WK7e09oIUyI/AAAAAAABB_A/ry22yAU3W9sbofMUmA5-nn3D45ix_Y5RwCLcB/s180-c/fruit_soldum.png"),
        ("corn", 50, r"https://1.bp.blogspot.com/-RAJBy7nx2Ro/XkZdTINEtOI/AAAAAAABXWE/x8Sbcghba9UzR8Ppafozi4_cdmD1pawowCNcBGAsYHQ/s180-c/vegetable_toumorokoshi_corn_wagiri.png"),
        ("aloe", 400, r"https://4.bp.blogspot.com/-v7OAB-ULlrs/VVGVQ1FCjxI/AAAAAAAAtjg/H09xS1Nf9_A/s180-c/plant_aloe_kaniku.png"),
    )
    with requests.Session() as session:
        FOOD_DATA = tuple(
            (name, price, c := session.get(image_url).content, detect_image_format(c))
            for name, price, image_url in FOOD_DATA
        )
    with sqlite3.connect(str(db_path)) as conn, closing(conn.cursor()) as cur:
        cur.execute("""
            CREATE TABLE Foods (
                name TEXT NOT NULL UNIQUE,
                price INT NOT NULL,
                image BLOB NOT NULL,
                image_type TEXT NOT NULL,
                PRIMARY KEY (name)
            );
        """)
        cur.executemany("INSERT INTO Foods(name, price, image, image_type) VALUES (?, ?, ?, ?)", FOOD_DATA)


KV_CODE = r'''
#:import ak asynckivy
#:import drop_active_touches kivyx.utils.drop_active_touches

<Label>:
    size_hint_min: [v + dp(8) for v in self.texture_size]
    halign: "center"

<SHFood>:
    orientation: "vertical"
    spacing: "4dp"
    size: "200dp", "200dp"
    size_hint: None, None
    canvas.before:
        Color:
            rgba: .4, .4, .4, 1
        Line:
            rectangle: (*self.pos, *self.size, )
    Image:
        fit_mode: "contain"
        texture: root.datum.texture
        size_hint_y: 3.
    Label:
        text: "{} ({} yen)".format(root.datum.name, root.datum.price)

<SHShelf@SemiRecycleBehavior+StackLayout>:
    padding: "10dp"
    spacing: "10dp"
    size_hint_min_y: self.minimum_height
    viewclass: "SHFood"

BoxLayout:
    orientation: "vertical"
    padding: "10dp"
    spacing: "10dp"
    BoxLayout:
        BoxLayout:
            orientation: "vertical"
            Label:
                text: "Shelf"
                font_size: max(20, sp(16))
                bold: True
                color: rgba("#44AA44")
            KXScrollView:
                size_hint_y: 1000.
                do_scroll_x: False
                vbar_enabled: True
                SHShelf:
                    id: shelf
        Splitter:
            sizable_from: "left"
            min_size: 100
            max_size: root.width
            BoxLayout:
                orientation: "vertical"
                Label:
                    text: "Your Shopping Cart"
                    font_size: max(20, sp(16))
                    bold: True
                    color: rgba("#4466FF")
                KXScrollView:
                    size_hint_y: 1000.
                    do_scroll_x: False
                    vbar_enabled: True
                    vbar_x: self.width - self.vbar_thickness
                    SHShelf:
                        id: cart
    BoxLayout:
        size_hint_y: None
        height: self.minimum_height
        spacing: "10dp"
        KXButton:
            text: "sort by price\n(ascend)"
            on_tap:
                drop_active_touches()
                shelf.data = sorted(shelf.data, key=lambda d: d.price)
        KXButton:
            text: "sort by price\n(descend)"
            on_tap:
                drop_active_touches()
                shelf.data = sorted(shelf.data, key=lambda d: d.price, reverse=True)
        KXButton:
            text: "sort by name\n(ascend)"
            on_tap:
                drop_active_touches()
                shelf.data = sorted(shelf.data, key=lambda d: d.name)
        KXButton:
            text: "sort by name\n(descend)"
            on_tap:
                drop_active_touches()
                shelf.data = sorted(shelf.data, key=lambda d: d.name, reverse=True)
        Widget:
        KXButton:
            id: total_price_btn
            text: "total price"
        KXButton:
            text: "sort by price\n(ascend)"
            on_tap:
                drop_active_touches()
                cart.data = sorted(cart.data, key=lambda d: d.price)
        KXButton:
            text: "sort by price\n(descend)"
            on_tap:
                drop_active_touches()
                cart.data = sorted(cart.data, key=lambda d: d.price, reverse=True)
'''


@dataclass(kw_only=True)
class Food:
    name: str = ""
    price: int = 0
    texture: F.Texture = None


class ShoppingApp(App):
    def build(self):
        return Builder.load_string(KV_CODE)

    def on_start(self):
        import os.path
        from random import randint

        from kivyx.gesture_detectors import long_press, horizontal_swipe
        from kivyx.uix.behaviors import drag_n_drop as dnd

        db_path = __file__ + r".sqlite3"
        if not os.path.exists(db_path):
            try:
                init_database(db_path)
            except Exception:
                os.remove(db_path)
                raise

        ids = self.root.ids
        shelf = ids.shelf
        cart = ids.cart
        shelf.data = [
            food
            for food in load_database(db_path)
            for __ in range(randint(2, 4))
        ]

        ak.managed_start(ak.wait_all(
            dnd.enable_drop_target_with_insertion_indicator(shelf),
            dnd.enable_drop_target_with_insertion_indicator(cart),
            dnd.enable_drag_for_children(shelf, triggers=(long_press, horizontal_swipe)),
            dnd.enable_drag_for_children(cart, triggers=(long_press, horizontal_swipe)),
            show_total_price_on_tap(ids.total_price_btn, cart),
        ))


async def show_total_price_on_tap(trigger_btn, cart: "SemiRecycleBehavior"):
    from kivyx.utils import drop_active_touches

    label = F.Label(
        size_hint=(.5, .2, ),
        font_size="40sp",
        halign="center",
        pos_hint={"center_x": .5, "center_y": .5, },
    )
    while True:
        await ak.event(trigger_btn, "on_tap")
        drop_active_touches()
        total_price = sum(d.price for d in cart.data)
        label.text = f"Total\n{total_price} yen"
        async with modal.open(label):
            await ak.sleep_forever()


class SHFood(F.BoxLayout):
    datum: Food = ObjectProperty(Food(), rebind=True)


class SemiRecycleBehavior:
    '''
    Mix-in class that adds RecyclewView-like interface to layouts.
    But unlike RecycleView, this one creates view widgets as much as the number of the data.
    '''

    viewclass = ObjectProperty()
    '''widget-class or its name'''

    def __init__(self, **kwargs):
        self._rv_refresh_params = {}
        self._rv_trigger_refresh = Clock.create_trigger(self._rv_refresh, -1)
        super().__init__(**kwargs)

    def on_viewclass(self, *args):
        self._rv_refresh_params["viewclass"] = None
        self._rv_trigger_refresh()

    def _get_data(self) -> Iterable:
        data = self._rv_refresh_params.get("data")
        return [c.datum for c in reversed(self.children)] if data is None else data

    def _set_data(self, new_data: Iterable):
        self._rv_refresh_params["data"] = new_data
        self._rv_trigger_refresh()

    data = property(_get_data, _set_data)

    def _rv_refresh(self, *args):
        viewclass = self.viewclass
        if not viewclass:
            self.clear_widgets()
            return
        data = self.data
        params = self._rv_refresh_params
        reusable_widgets = "" if "viewclass" in params else self.children[::-1]
        self.clear_widgets()
        if isinstance(viewclass, str):
            viewclass = F.get(viewclass)
        for datum, w in zip(data, itertools.chain(reusable_widgets, iter(viewclass, None))):
            w.datum = datum
            self.add_widget(w)
        params.clear()


F.register("SemiRecycleBehavior", cls=SemiRecycleBehavior)


if __name__ == "__main__":
    ShoppingApp().run()
