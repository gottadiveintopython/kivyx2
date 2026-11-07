__all__ = (
    "noop", "CancellableTimer", "copy_layout_state", "visibility_aware_touch_movements",
    "drop_active_touches", "drop_touch", "find_child_at", "find_child_with_index_at",
    "compute_velocity", "record_touch_movement",
)

from collections.abc import Reversible
from collections import deque
from copy import deepcopy
from contextlib import asynccontextmanager, ExitStack, contextmanager
from typing import Union

from kivy.clock import Clock
from kivy.base import EventLoop
from kivy.core.window import Window, WindowBase
from kivy.uix.widget import Widget
import asynckivy as ak

type Wow = WindowBase | Widget


def noop(*args, **kwargs):
    """
    A function that does nothing.
    """


class CancellableTimer:
    '''
    Full async wrapper for :class:`~kivy.clock.ClockEvent`
    '''
    __slots__ = ("start", "cancel", "wait_expiration", )

    def __init__(self, timeout: float, *, event=None):
        if event is None:
            event = ak.Event()
        ce = Clock.create_trigger(event.fire, timeout, False, False)
        self.wait_expiration = event.wait
        self.start = ce
        self.cancel = ce.cancel


_shallow_copyable_layout_property_names = (
    "x", "y", "width", "height",
    "size_hint_x", "size_hint_y",
    "size_hint_min_x", "size_hint_min_y",
    "size_hint_max_x", "size_hint_max_y",
)


def copy_layout_state(from_, to_):
    '''
    Copies the layout-related properties from one to another.

    .. code-block::

        to_.x = from_.x
        to_.y = from_.y
        to_.width = from_.width
        ...
        to_.pos_hint = deepcopy(from_.pos_hint)
    '''
    setattr_ = setattr
    getattr_ = getattr
    for name in _shallow_copyable_layout_property_names:
        setattr_(to_, name, getattr_(from_, name))
    setattr_(to_, "pos_hint", deepcopy(getattr_(from_, "pos_hint")))


@asynccontextmanager
async def visibility_aware_touch_movements(widget, touch):
    '''
    Allows you to detect whether touch movement occurs within the visible area of a widget.
    You might want to use this when the widget is partially clipped by other widgets, such as ``KXScrollView``.

    .. code-block::

        import asynckivy as ak

        async with(
            ak.move_on_when(touch.ud["kivyx_touch_up"].wait()),
            visibility_aware_touch_movements(widget, touch) as on_touch_move,
        ):
            was_inside = ...
            while True:
                is_inside = await on_touch_move()
                if is_inside:
                    if was_inside:
                        print("Touch moved while staying within the visible area")
                    else:
                        print("Touch moved from outside to inside the visible area")
                else:
                    if was_inside:
                        print("Touch moved from inside to outside the visible area")
                    else:
                        print("Touch moved while staying outside the visible area")
                was_inside = is_inside

    .. note::
        The touch is always in window coordinates when the ``await on_touch_move()`` returns.
    '''
    inside = None
    e = ak.ExclusiveEvent()
    trigger_wakeup = Clock.create_trigger(lambda dt, fire=e.fire: fire(inside), -1)

    def on_touch_move(w, t, touch=touch, collide_point=widget.collide_point):
        nonlocal inside
        if t is touch and collide_point(*t.pos):
            inside = True

    def on_touch_move_win(w, t, touch=touch, trigger_wakeup=trigger_wakeup):
        nonlocal inside
        if t is touch:
            inside = False
            trigger_wakeup()

    with ExitStack() as stack:
        defer = stack.callback
        defer(trigger_wakeup.cancel)
        defer(Window.unbind_uid, "on_touch_move", Window.fbind("on_touch_move", on_touch_move_win))
        defer(widget.unbind_uid, "on_touch_move", widget.fbind("on_touch_move", on_touch_move))
        yield e.wait_args_0


def drop_active_touches():
    '''
    Instructs ``kivyx`` to drop all currently active touches. Any ongoing gestures will be cancelled,
    and the library will ignore any further motion of those touches.

    You may want to call this when your app switches a scene.
    '''
    for t in reversed(EventLoop.touches):
        try:
            abandon = t.ud["kivyx_abandon"]
        except KeyError:
            continue
        abandon.fire()


def drop_touch(touch):
    '''
    Instructs ``kivyx`` to drop a specific touch. Any ongoing gestures associated with that touch
    will be cancelled, and the library will ignore any further motion of that touch.
    '''
    try:
        abandon = touch.ud["kivyx_abandon"]
    except KeyError:
        return
    abandon.fire()


def find_child_at(children, x, y) -> Union[Widget, None]:
    '''
    Returns the child widget at the given position, or ``None`` if no child is found.
    '''
    for c in children:
        if c.collide_point(x, y):
            return c
    return None


def find_child_with_index_at(children, x, y) -> Union[tuple[Widget, int], tuple[None, None]]:
    '''
    Returns a tuple ``(widget, index)`` for the child widget at the given position,
     or ``(None, None)`` if no child is found.
    '''
    for i, child in enumerate(children):
        if child.collide_point(x, y):
            return (child, i)
    return (None, None)


@contextmanager
def record_touch_movement(receiver: Wow, touch, *, limit: int | None=None, include_initial=False):
    '''
    Returns a context manager that records the movement of the specified touch.

    .. code-block::

        with record_touch_movement(widget, touch) as records:
            # records will contain tuples of (time, dx, dy) for each movement of the touch

    :param receiver:
        The Widget or WindowBase instance to be used to receive ``on_touch_move`` events.

    :param touch:
        The MotionEvent whose movement is to be tracked.

    :param limit:
        The maximum number of records to keep. If ``None``, all records are kept.
        Otherwise, only the most recent records are kept, up to this limit.

    :param include_initial:
        If ``True``, the initial state of the touch at the time of entering the context
        is included in the records.
    '''
    records = deque(maxlen=limit)
    if include_initial:
        records.append((touch.time_update, touch.dx, touch.dy))

    def on_touch_move(w, t, append=records.append, touch=touch):
        if t is touch:
            append((touch.time_update, touch.dx, touch.dy))
    bind_id = receiver.fbind("on_touch_move", on_touch_move)
    try:
        yield records
    finally:
        receiver.unbind_uid("on_touch_move", bind_id)


def compute_velocity(
    movement_records: Reversible[tuple[float, float, float]],
    *, time_window=1 / 6, fallback=(0., 0.),
) -> tuple[float, float]:
    '''
    Computes the average velocity from the given movement records.

    .. code-block::

        with record_touch_movement(widget, touch) as records:
            ...
        velocity_x, velocity_y = compute_velocity(records)

    :param movement_records:
        Movement records in chronological order, each consisting of ``(time, dx, dy)``.

    :param time_window:
        The maximum time interval (in seconds) to consider for computing the velocity.
        Only records within this time window from the most recent record are used.
    '''
    # 移動量と経過時間から速度を求めるだけの単純な計算に思えるが、
    # 植木算のような考え方が求められるので注意 (時刻が植木で移動量が間隔)。
    # 例えば movement_records の中身を [(t0, dx0, dy0), (t1, dx1, dy1), ...] と表すとする。
    # この時 dx1, dy1 進むのにかかった時間は t1 - t0 である。
    # じゃあ dx0, dy0 進むのにかかった時間はというと、それ以前の記録が無いので算出できない。
    records = reversed(movement_records)
    first = next(records, None)
    if first is None:
        return fallback
    time_end, prev_dx, prev_dy = first
    time_start = time_end
    total_dx = total_dy = 0.
    deadline = time_end - time_window
    for t, dx, dy in records:
        time_start = t
        total_dx += prev_dx
        total_dy += prev_dy
        if t < deadline:
            break
        prev_dx = dx
        prev_dy = dy

    duration = time_end - time_start
    if duration <= 0.:
        return fallback
    return total_dx / duration, total_dy / duration
