__all__ = []


def immediate_call(f):
    f()


@immediate_call
def register_components():
    from kivy.factory import Factory
    r = Factory.register

    # Behaviors
    r("KXMultiTapGestureRecognizer", module="kivyx.uix.behaviors.tap")
    r("KXTapGestureRecognizer", module="kivyx.uix.behaviors.tap")
    r("KXTouchRippleBehavior", module="kivyx.uix.behaviors.touchripple")

    # Widgets
    r("KXButton", module="kivyx.uix.button")
    r("KXMultiTapButton", module="kivyx.uix.button")
    r("KXScrollView", module="kivyx.uix.scrollview")
    r("KXSwitch", module="kivyx.uix.switch")


@immediate_call
def setup_signals():
    import types
    from kivy.core.window import Window

    class LifoEvent:
        '''
        :class:`asyncgui.StatefulEvent` に以下の変更を加えた物。

        * 待ちに入った順とは逆にタスク達を起こす。
        * 値の受け渡しを行わない。
        * ``clear()`` メソッドを削除。
        '''
        __slots__ = ('is_fired', '_waiting_tasks', )

        def __init__(self):
            self.is_fired = False
            self._waiting_tasks = []

        def fire(self, *args, **kwargs):
            if self.is_fired:
                return
            self.is_fired = True
            for t in reversed(self._waiting_tasks):
                if t is not None:
                    t._step()

        @types.coroutine
        def wait(self, len=len):
            if self.is_fired:
                return
            tasks = self._waiting_tasks
            idx = len(tasks)
            try:
                return (yield tasks.append)
            finally:
                tasks[idx] = None

    def put_signals(w, t, E=LifoEvent):
        ud = t.ud
        ud["kivyx_claim_signal"] = E()
        ud["kivyx_end_signal"] = E()

    def fire_signals(w, t):
        ud = t.ud
        ud["kivyx_end_signal"].fire()
        ud["kivyx_claim_signal"].fire()

    Window.fbind("on_touch_down", put_signals)
    Window.fbind("on_touch_up", fire_signals)
