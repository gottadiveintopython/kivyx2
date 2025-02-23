from textwrap import dedent
import pytest
from kivy.lang import Builder
from kivyx.uix.scrollview import KXScrollView


def test_zero_sized_content(kivy_clock):
    sv: KXScrollView = Builder.load_string(dedent("""
    KXScrollView:
        size: 100, 100
        Widget:
            size_hint: None, None
            size: 0, 0
    """))
    kivy_clock.tick()
    assert sv.size == [100, 100]
    assert sv.content.size == [0, 0]
    assert sv.content_min_x == 0
    assert sv.content_min_y == 0
    assert sv.content_max_x == 100
    assert sv.content_max_y == 100


def test_zero_sized_scrollview(kivy_clock):
    sv: KXScrollView = Builder.load_string(dedent("""
    KXScrollView:
        size: 0, 0
        Widget:
            size_hint: None, None
            size: 100, 100
    """))
    kivy_clock.tick()
    assert sv.size == [0, 0]
    assert sv.content.size == [100, 100]
    assert sv.content_min_x == -100
    assert sv.content_min_y == -100
    assert sv.content_max_x == 0
    assert sv.content_max_y == 0


def test_zero_sized_scrollview_and_content(kivy_clock):
    sv: KXScrollView = Builder.load_string(dedent("""
    KXScrollView:
        size: 0, 0
        Widget:
            size_hint: None, None
            size: 0, 0
    """))
    kivy_clock.tick()
    assert sv.size == [0, 0]
    assert sv.content.size == [0, 0]
    assert sv.content_min_x == 0
    assert sv.content_min_y == 0
    assert sv.content_max_x == 0
    assert sv.content_max_y == 0


@pytest.mark.parametrize('size', [(0, 0), (100, 0), (0, 100), (100, 100)])
def test_same_sized_scrollview_and_content(kivy_clock, size):
    sv: KXScrollView = Builder.load_string(dedent("""
    KXScrollView:
        Widget:
            size_hint: 1, 1
    """))
    sv.size = size
    kivy_clock.tick()
    kivy_clock.tick()
    assert sv.size == list(size)
    assert sv.content.size == list(size)
    assert sv.content_min_x == 0
    assert sv.content_min_y == 0
    assert sv.content_max_x == 0
    assert sv.content_max_y == 0


def test_scroll_to_content_itself(kivy_clock):
    sv: KXScrollView = Builder.load_string(dedent("""
    KXScrollView:
        Widget:
    """))
    kivy_clock.tick()
    with pytest.raises(ValueError):
        sv.scroll_to_widget(sv.content)


def test_scroll_to_scrollview_itself(kivy_clock):
    sv: KXScrollView = Builder.load_string(dedent("""
    KXScrollView:
        Widget:
    """))
    kivy_clock.tick()
    with pytest.raises(ValueError):
        sv.scroll_to_widget(sv)
