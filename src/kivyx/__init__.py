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
def setup_claim_signal():
    import asyncgui
    from kivy.core.window import Window

    def put_signal(w, t, Event=asyncgui.StatefulEvent):
        t.ud["kivyx_claim_signal"] = Event()

    Window.fbind("on_touch_down", put_signal)
