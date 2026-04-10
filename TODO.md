# KXScrollView

- Align its behavior with the official (Kivy 3.0.0) implementation.
- ScrollViewの領域外にスクロールバーを置けるようにする。
- `effects` モジュールを `Carousel` を見据えた設計にする。
- Needs significant refactoring.
- Needs a lot of unit tests

# etc

- ~~`drag_timeout` や `scroll_distance` の初期値を格納するmoduleを作る。~~

```python
class EventDispatcher:
    def dispatch(self, event_type, *largs, **kwargs):
        ...
```

- Add a Kivy 3.0.0 `ButtonBehavior` equivalent.
- Look into `kivy.eventmanager` and use it if appropriate.
- Add `Carousel`.
- Add `Drawer`.
- ~~Add a custom touch ring, as `kivy.modules.touchring` is broken in Kivy 2.x.~~
