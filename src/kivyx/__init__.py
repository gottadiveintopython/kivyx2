__all__ = []


def immediate_call(f):
    f()


@immediate_call
def register_components():
    from kivy.factory import Factory
    r = Factory.register

    # Behaviors
    r('KXDraggableBehavior', module="kivyx.uix.behaviors.draggable")
    r('KXDragReorderBehavior', module="kivyx.uix.behaviors.draggable")
    r('KXDragTargetBehavior', module="kivyx.uix.behaviors.draggable")
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

    class StatefulLifoEvent:
        '''
        :class:`asyncgui.StatefulEvent` with the following differences:

        * :meth:`fire` wakes up waiting tasks in the *reverse* order they started waiting.
        * Does not have ``clear()`` method.
        * The values passed to :meth:`fire` is discarded,
          and ``await event.wait()`` always returns ``None``.
        * Methods have aliases to improve the readability of user-side code.
        '''
        __slots__ = ('_is_fired', '_waiting_tasks', )

        def __init__(self):
            self._is_fired = False
            self._waiting_tasks = []

        def fire(self, *args, **kwargs):
            if self._is_fired:
                return
            self._is_fired = True
            for t in reversed(self._waiting_tasks):
                if t is not None:
                    t._step()

        @property
        def is_fired(self):
            return self._is_fired

        @types.coroutine
        def wait(self, _len=len):
            if self._is_fired:
                return
            tasks = self._waiting_tasks
            idx = _len(tasks)
            try:
                yield tasks.append
            finally:
                tasks[idx] = None

        claim = fire
        has_been_claimed = is_fired
        wait_for_someone_to_claim = wait

    def put_events(w, t, E=StatefulLifoEvent):
        ud = t.ud
        ud["kivyx_exclusive_access"] = E()
        ud["kivyx_end_event"] = E()

    def fire_events(w, t):
        ud = t.ud
        ud["kivyx_end_event"].fire()
        ud["kivyx_exclusive_access"].fire()

    Window.fbind("on_touch_down", put_events)
    Window.fbind("on_touch_up", fire_events)
