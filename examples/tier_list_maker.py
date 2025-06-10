'''
https://youtu.be/zHEdcsq0QXo
'''

from collections.abc import Iterable
from contextlib import closing
from os import PathLike
import sqlite3
from dataclasses import dataclass

from kivy.properties import ObjectProperty
from kivy.app import App
from kivy.lang import Builder
from kivy.factory import Factory as F
import asynckivy as ak

from kivyx.uix.behaviors.draggable import KXDraggableBehavior


def detect_image_format(image_data: bytes) -> str:
    if image_data.startswith(b"\x89\x50\x4E\x47\x0D\x0A\x1A\x0A"):
        return "png"
    elif image_data.startswith(b"\xFF\xD8"):
        return "jpg"
    raise ValueError("Unknown image format")


KV_CODE = r'''
#:set ITEM_WIDTH dp(100)
#:set ITEM_HEIGHT dp(100)
#:set ITEM_SIZE (ITEM_WIDTH, ITEM_HEIGHT)
#:set MIN_ROW_HEIGHT dp(120)

<ReorderableBoxLayout@KXDragReorderBehavior+BoxLayout>:
<ReorderableStackLayout@KXDragReorderBehavior+StackLayout>:

<TLMItem>:
    drag_cls: "TLMItem"
    drag_timeout: 0
    size: ITEM_SIZE
    size_hint: None, None
    opacity: .5 if self.is_being_dragged else 1.
    fit_mode: "contain"
    texture: self.datum.texture

<TLMRow@KXDraggableBehavior+ReorderableStackLayout>:
    padding: [dp(30), dp(10), dp(10), dp(10)]
    spacing: "10dp"
    size_hint_min_y: max(self.minimum_height, MIN_ROW_HEIGHT)
    drag_cls: "TLMRow"
    drag_classes: ["TLMItem", ]
    drag_timeout: 0.01
    opacity: .5 if self.is_being_dragged else 1.
    canvas.before:
        Color:
            rgba: .8, .8, .8, 1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: dp(20), dp(20)

<TierListMaker>:
    orientation: "vertical"
    padding: "10dp"
    spacing: "10dp"
    KXScrollView:
        size_hint_y: 3
        do_scroll_x: False
        vbar_enabled: True
        vbar_x: self.width - self.vbar_thickness
        ReorderableBoxLayout:
            id: rows
            spacing: "10dp"
            size_hint_min_y: self.minimum_height
            orientation: "vertical"
            drag_classes: ["TLMRow", ]
    Splitter:
        height: MIN_ROW_HEIGHT
        sizable_from: "top"
        min_size: 0
        KXScrollView:
            do_scroll_x: False
            vbar_enabled: True
            ReorderableStackLayout:
                id: uncategorized
                drag_classes: ["TLMItem", ]
                size_hint_min_y: max(self.minimum_height, MIN_ROW_HEIGHT)
'''


@dataclass
class Datum:
    name: str = ''
    texture: F.Texture = None


class TestApp(App):
    def build(self):
        Builder.load_string(KV_CODE)
        return TierListMaker()

    def on_start(self):
        import os.path
        db_path = __file__ + r".sqlite3"
        if not os.path.exists(db_path):
            try:
                self._init_database(db_path)
            except Exception:
                os.remove(db_path)
                raise
        ak.managed_start(self.root.main(self._load_from_database(db_path)))

    def on_stop(self):
        self.print_tiers(self.root.current_tiers())

    @staticmethod
    def print_tiers(tiers: list[list[Datum]]):
        for tier in tiers:
            print([datum.name for datum in tier])

    @staticmethod
    def _load_from_database(db_path: PathLike) -> list[Datum]:
        from io import BytesIO
        from kivy.core.image import Image as CoreImage

        with sqlite3.connect(str(db_path)) as conn:
            # FIXME: It's probably better to ``Texture.add_reload_observer()``.
            return [
                Datum(name=name, texture=CoreImage(BytesIO(image_data), ext=image_type).texture)
                for name, image_data, image_type in conn.execute("SELECT name, image, image_type FROM Foods")
            ]

    @staticmethod
    def _init_database(db_path: PathLike):
        import requests
        FOOD_DATA = (
            # (name, image_url)
            ("blueberry", r"https://3.bp.blogspot.com/-RVk4JCU_K2M/UvTd-IhzTvI/AAAAAAAAdhY/VMzFjXNoRi8/s180-c/fruit_blueberry.png"),
            ("cacao", r"https://3.bp.blogspot.com/-WT_RsvpvAhc/VPQT6ngLlmI/AAAAAAAAsEA/aDIU_F9TYc8/s180-c/fruit_cacao_kakao.png"),
            ("dragon fruit", r"https://1.bp.blogspot.com/-hATAhM4UmCY/VGLLK4mVWYI/AAAAAAAAou4/-sW2fvsEnN0/s180-c/fruit_dragonfruit.png"),
            ("kiwi", r"https://2.bp.blogspot.com/-Y8xgv2nvwEs/WCdtGij7aTI/AAAAAAAA_fo/PBXfb8zCiQAZ8rRMx-DNclQvOHBbQkQEwCLcB/s180-c/fruit_kiwi_green.png"),
            ("lemon", r"https://2.bp.blogspot.com/-UqVL2dBOyMc/WxvKDt8MQbI/AAAAAAABMmk/qHrz-vwCKo8okZsZpZVDsHLsKFXdI1BjgCLcBGAs/s180-c/fruit_lemon_tategiri.png"),
            ("mangosteen", r"https://4.bp.blogspot.com/-tc72dGzUpww/WGYjEAwIauI/AAAAAAABAv8/xKvtWmqeKFcro6otVdLi5FFF7EoVxXiEwCLcB/s180-c/fruit_mangosteen.png"),
            ("apple", r"https://4.bp.blogspot.com/-uY6ko43-ABE/VD3RiIglszI/AAAAAAAAoEA/kI39usefO44/s180-c/fruit_ringo.png"),
            ("orange", r"https://1.bp.blogspot.com/-fCrHtwXvM6w/Vq89A_TvuzI/AAAAAAAA3kE/fLOFjPDSRn8/s180-c/fruit_slice10_orange.png"),
            ("soldum", r"https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEhCfc1u49DKy98iG2coZ8um6YnShx_2T57_lZfEGeeGS0Kt6xQsI0GOpKIlq6jwzn_Wdw7QlMcKRXlo8A22sBySaesOh7_OHBRALxZZSEbFIJa-54NnEY9s0xWZX4S-oDCrXk1oApW8jdJ_/s400/fruit_soldum.png"),
            ("corn", r"https://1.bp.blogspot.com/-RAJBy7nx2Ro/XkZdTINEtOI/AAAAAAABXWE/x8Sbcghba9UzR8Ppafozi4_cdmD1pawowCNcBGAsYHQ/s180-c/vegetable_toumorokoshi_corn_wagiri.png"),
            ("aloe", r"https://4.bp.blogspot.com/-v7OAB-ULlrs/VVGVQ1FCjxI/AAAAAAAAtjg/H09xS1Nf9_A/s180-c/plant_aloe_kaniku.png"),
            ("peach", r"https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEjFR0u6sU9SO2EmpdDbkWhRm0BNGTL025PCVABYGZj4tG7IZ3B7erC7IIhOEJfzjp2NXRLQcO7XWSsl4PdlKsUtkoiLnH8PRaClVmSb8ASmzoQ48mx7jQpzPsJd89IXH5DUq3HYMZLfyi0M/s180-c/fruit_momo.png"),
            ("grape", r"https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEjjIjHS99uNo_1ym0yRc7qrG0kEIUX_FfjwujAwE3-p5CHAUIYapoc0qQsAgSvJh4zqq5Bvs5NedLH0CwkVeqLw-KYnXtFMXWJKkhlZ-vJyB4DxZhRr8yM-gUb6IC-jKzW2JnAfXRNLLX5T/s180-c/fruit_budou_kyohou.png"),
            ("prune", r"https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEjdvXI2LjHNMI01Qp_SPP75sKYxcwKyYYA1F60bdR7rDn91r_eDowQctSHUURo4wIaemBcZsiaiVI9LrYHLmobr2yKPg5DjkXfQt5fcnM3jgH8A66dU0s1xo2Wo0m-m_kYBgdVkEglIm7U/s180-c/fruit_prune.png"),
            ("watermelon", r"https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEiIGzs925zRMgLU60x1bPyZVKdh5ehbjxzZx3sA_yTQMuys2pV6QmND89tbPiQ4aTz7PPTNSmr1OBD2M35_iadW9yHHlGJMvwVw_KjSKg_E0rXUfaOZhCxcNvR-Tthy0gwE8sS1gwuq8v2g/s180-c/fruit_suika_kodama.png"),
            ("cranberry", r"https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEi7cDScGAI8TAToSkGeDA24Vk1qFm9CUxpPnkvejWhv3EvUriJh7sDQL2I_jWCIB0xNPnwoHCh12hrPnA0l6JQ3jU0H3nrz2yuRLMYcMT3jJI91AkBz62dpEhPhg_Crel83wc4LndtNBSw/s180-c/fruit_cranberry.png"),
            ("raspberry", r"https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEi_GddUrtIH534qGyXIHfbSZHH-kqUzOGXPGaFxVMvsvLhGLxVeZlgEWk2Wu7LOtMWsHo8LT_VHKFiLUIcY_uXmYcuvMtnABLvasq1uh0EzomV38JoXzB36YNLftrlRcTOPjKsu4THxuD1E/s180-c/fruit_raspberry_heta.png"),
            ("cherry", r"https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEjPKiPjI_IBEx_KGG48ujAA3JYiRuD6h10m8kANkVMVtw3dCxpn8g-nqotffCsvdpqcvyAVo0cvUIR6wgVjUEYyAHbFqnfF1HoeM2QaW27mdeq-NG_zze3hAexK9kywdK-zzQ_Tt7qxjcjR/s180-c/fruit_sakuranbo.png"),
            ("chestnut", r"https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEj0Ub4d-thPZSpyeEq2Br0gtja34LYhpa_Ms92Z4Gp-woa4VxfQiG44PGhMGqXbrPZum4Kx0sE5qCzsVSvmG7myyts-vZBP2tJngghydoZRmFsZuMN5f8YqLjeo6SwVCCYyCLK3qtjSgjzX/s180-c/kuri.png"),
            ("persimmon", r"https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEjyuTiQjRSYySmv2mZ2M-hFEbiy7FkzJP9xbZkhKDf7COnbnnOkpRSU8t9E7Fr78TMwjz8B-E36FWAG1G8YY55pBbCmqls3VL-k5SLa_JBl_gceAPIA9pskA0pilG2ptRj498ms-NNuwbJR/s400/fruit_kaki.png"),
            ("banana", r"https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEjDTy81qEYQ7MLvImTaqiWn_8Wu16qPSIVeJP0Aae64gv07aXn1vB7bYczEbPjMqj-CEgAe9DMTD4KkQ2kq83y1tYUcJF3RbF7LJAe0qZLRVwd667uFMHukkjcEC1rzWheoOtGI1eqhCywi/s180-c/fruit_banana.png"),
            ("avocado", r"https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEgoKZ3Ij4CTbPpLLOtOkiga04gbT7adXrRRoLLr0gke57V4pHUneaIQ2rSmZLoNPGbSvhnl8IIZ3SyDGUL2EGl3Slt4QxaP4AQS5IcbTrSIq9JrMMFH2UsXa9zvGCQEtRtAMtpA6DJnFiuJ/s400/fruit_avocado.png"),
        )
        with requests.Session() as session:
            FOOD_DATA = tuple(
                (name, c := session.get(image_url).content, detect_image_format(c))
                for name, image_url in FOOD_DATA
            )
        with sqlite3.connect(str(db_path)) as conn, closing(conn.cursor()) as cur:
            cur.execute("""
                CREATE TABLE Foods (
                    name TEXT NOT NULL UNIQUE,
                    image BLOB NOT NULL,
                    image_type TEXT NOT NULL,
                    PRIMARY KEY (name)
                );
            """)
            cur.executemany("INSERT INTO Foods(name, image, image_type) VALUES (?, ?, ?)", FOOD_DATA)


class TLMItem(KXDraggableBehavior, F.Image):
    datum: Datum = ObjectProperty(Datum(), rebind=True)


class TierListMaker(F.BoxLayout):
    async def main(self, data: Iterable[Datum], *, n_tiers=5):
        TLMRow = F.TLMRow
        rows = self.ids.rows
        for __ in range(n_tiers):
            rows.add_widget(TLMRow())

        TLMItem = F.TLMItem
        uncategorized = self.ids.uncategorized
        for datum in data:
            uncategorized.add_widget(TLMItem(datum=datum))

        await ak.n_frames(2)
        uncategorized.parent.scroll_to_pos(y=-2000)

    def current_tiers(self) -> list[list[Datum]]:
        return [
            [item.datum for item in row.children]
            for row in reversed(self.ids.rows.children)
        ]


if __name__ == "__main__":
    TestApp(title="Tier List Maker").run()
