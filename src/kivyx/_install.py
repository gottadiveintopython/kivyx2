__all__ = ("install_on_factory", "install_on_window", )
import types
from functools import cache
from collections import defaultdict

import asynckivy as ak

from kivyx.gesture_detectors import detectors as gesture_detectors


@cache
def install_on_factory(factory):
    r = factory.register
    r("KXButton", module="kivyx.uix.button")
    r("KXDrawer", module="kivyx.uix.drawer")
    r("KXDrawerTab", module="kivyx.uix.drawer")
    r("KXScrollView", module="kivyx.uix.scrollview")
    r("KXSwitch", module="kivyx.uix.switch")


class LifoStatefulEvent:
    '''
    A :class:`asyncgui.StatefulEvent` with the following differences:

    - A Task that starts waiting later resumes earlier (hence the ``Lifo`` prefix).
    - Can be fired only once (there is no ``clear`` method).
    - The ``fire`` method does not accept keyword arguments. Consequently,
      :attr:`params` returns the positional arguments passed to :meth:`fire`.
    '''
    __slots__ = ("_params", "_waiting_tasks", )

    def __init__(self):
        self._params = None
        self._waiting_tasks = []

    @property
    def is_fired(self) -> bool:
        return self._params is not None

    def fire(self, *params):
        if self.is_fired:
            raise ak.InvalidStateError("Already fired.")
        self._params = params
        for t in reversed(self._waiting_tasks):
            if t is not None:
                t._step(*params)

    @types.coroutine
    def wait(self, _len=len):
        if (p := self._params) is not None:
            return p
        tasks = self._waiting_tasks
        idx = _len(tasks)
        try:
            return (yield tasks.append)[0]
        finally:
            tasks[idx] = None

    @property
    def params(self) -> tuple:
        if (p := self._params) is None:
            raise ak.InvalidStateError("Has not been fired.")
        return p

    has_been_claimed = is_fired
    claim = fire
    wait_for_someone_to_claim = wait


async def _detect_gestures_and_notify_listeners(window, touch, ak=ak, gesture_detectors=gesture_detectors):
    await ak.sleep(-1)
    ud = touch.ud
    events: list[LifoStatefulEvent] = []
    tasks = await ak.wait_any(*[
        (events.append(event), ) and gesture_detectors[gesture_name](window, touch)
        for gesture_name, event in ud["kivyx_gestures"].items()
    ])
    for task, event in zip(tasks, events):
        if task.finished:
            event.fire()
            return


def _put_stuff_into_touch_ud(window, touch, defaultdict=defaultdict, LifoEvent=LifoStatefulEvent, ak=ak):
    ud = touch.ud
    ud["kivyx_exclusive_access"] = LifoEvent()
    ud["kivyx_touch_up"] = LifoEvent()
    ud["kivyx_abandon"] = LifoEvent()
    ud["kivyx_gestures"] = defaultdict(LifoEvent)
    ud["_kivyx_gesture_notifier"] = ak.start(_detect_gestures_and_notify_listeners(window, touch))


def _notify_of_touch_up(window, touch):
    ud = touch.ud
    ud["_kivyx_gesture_notifier"].cancel()
    ud["kivyx_touch_up"].fire()


@cache
def install_on_window(window):
    window.fbind("on_touch_down", _put_stuff_into_touch_ud)
    window.fbind("on_touch_up", _notify_of_touch_up)
