__all__ = []


def immediate_call(f):
    f()


@immediate_call
def register_components_to_factory():
    from kivy.factory import Factory
    r = Factory.register

    # Behaviors
    r('KXDraggableBehavior', module="kivyx.uix.behaviors.drag_n_drop")
    r('KXDropTargetBehavior', module="kivyx.uix.behaviors.drag_n_drop")
    r('KXDropTargetBehaviorWithInsertionIndicator', module="kivyx.uix.behaviors.drag_n_drop")
    r("KXMultiTapGestureRecognizer", module="kivyx.uix.behaviors.multitap")
    r("KXSwipe2DeleteBehavior", module="kivyx.uix.behaviors.swipe2delete")
    r("KXTapGestureRecognizer", module="kivyx.uix.behaviors.tap")
    r("KXTouchRippleBehavior", module="kivyx.uix.behaviors.touchripple")

    # Widgets
    r("KXButton", module="kivyx.uix.button")
    r("KXMultiTapButton", module="kivyx.uix.button")
    r("KXScrollView", module="kivyx.uix.scrollview")
    r("KXSwitch", module="kivyx.uix.switch")


@immediate_call
def setup_events():
    import types
    from kivy.core.window import Window

    class ExclusiveAccess:
        __slots__ = ("_params", "_waiting_tasks", )

        def __init__(self):
            self._params = None
            self._waiting_tasks = []

        @property
        def has_been_claimed(self) -> bool:
            return self._params is not None

        def claim(self, *params):
            '''
            .. code-block::

                ex_access = touch.ud["kivyx_exclusive_access"]
                if ex_access.has_been_claimed:
                    return
                ex_access.claim(claimant, ...)

            :raises Exception: If exclusive access has already been claimed.
            '''
            if self.has_been_claimed:
                raise Exception("Exclusive access has already been claimed.")
            self._params = params
            for t in self._waiting_tasks:
                if t is not None:
                    t._step(*params)

        @types.coroutine
        def wait_for_one_to_claim(self, _len=len):
            '''
            .. code-block::

                ex_access = touch.ud["kivyx_exclusive_access"]
                claimant, *__ = await ex_access.wait_for_one_to_claim()
            '''
            if self.has_been_claimed:
                return self._params
            tasks = self._waiting_tasks
            idx = _len(tasks)
            try:
                return (yield tasks.append)[0]
            finally:
                tasks[idx] = None

        @property
        def params(self) -> tuple:
            '''
            :raises Exception: If exclusive access has not been claimed.
            '''
            if (p := self._params) is None:
                raise Exception("Exclusive access has not been claimed.")
            return p

    class LifoEvent:
        '''
        An :class:`asyncgui.StatefulEvent` with the following differences:

        - A task that starts waiting later wakes up earlier.
        - No ``clear`` method.
        - No value-passing mechanism: the ``fire`` method takes no arguments.
        '''
        __slots__ = ("_is_fired", "_waiting_tasks", )

        def __init__(self):
            self._is_fired = False
            self._waiting_tasks = []

        @property
        def is_fired(self) -> bool:
            return self._is_fired

        def fire(self):
            if self._is_fired:
                return
            self._is_fired = True
            for t in reversed(self._waiting_tasks):
                if t is not None:
                    t._step()

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

    def put_stuff(w, t, EAccess=ExclusiveAccess, LifoEvent=LifoEvent):
        ud = t.ud
        ud["kivyx_exclusive_access"] = EAccess()
        ud["kivyx_end"] = LifoEvent()
        ud["kivyx_abandon"] = LifoEvent()

    def fire_end_event(w, t):
        # This should be the only place to fire the 'kivyx_end'.
        t.ud["kivyx_end"].fire()

    Window.fbind("on_touch_down", put_stuff)
    Window.fbind("on_touch_up", fire_end_event)
