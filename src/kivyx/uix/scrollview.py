__all__ = ('KXScrollView', )

from functools import partial
from collections import deque
from contextlib import contextmanager, ExitStack

from kivy.lang import Builder
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.widget import Widget
from kivy.uix.scrollview import ScrollView as SV
from kivy.properties import NumericProperty, BooleanProperty, ObjectProperty, ReferenceListProperty, ColorProperty
import asynckivy as ak

from kivyx.touch_filters import is_opos_colliding
from kivyx.effects.scroll import KXScrollEffect
from kivyx.effects.dampedscroll import KXDampedScrollEffect


Builder.load_string('''
<KXScrollView>:
    _content_x: self.content_x
    _content_y: self.content_y
    canvas.before:
        PushMatrix:
        Translate:
            x: self.x
            y: self.y
        StencilPush
        Rectangle:
            pos: 0, 0
            size: self.size
        StencilUse:
        Translate:
            x: self.content_x
            y: self.content_y
    canvas.after:
        Translate:
            x: -self.content_x
            y: -self.content_y
        Color:
            rgba: self.hbar_color
        Rectangle:
            size: self._hbar_length, self.hbar_thickness
            pos: self.hbar_x, self.hbar_y
        Color:
            rgba: self.vbar_color
        Rectangle:
            size: self.vbar_thickness, self._vbar_length
            pos: self.vbar_x, self.vbar_y
        StencilUnUse
        Rectangle:
            pos: 0, 0
            size: self.size
        StencilPop:
        PopMatrix:
''')


def clamp(value, min, max):
    return max if value >= max else (min if value <= min else value)


def compute_velocity(touch_history, timeout=10./60.):
    '''
    .. code-block::

        velocity_x, velocity_y = compute_velocity(touch_history)
    '''
    touch_history = reversed(touch_history)
    time_end, dx_sum, dy_sum = next(touch_history)
    time_start = time_end
    deadline = time_end - timeout
    for t, dx, dy in touch_history:
        if t < deadline:
            break
        dx_sum += dx
        dy_sum += dy
        time_start = t
    if time_start is time_end:
        return 0, 0
    duration = time_end - time_start
    return dx_sum / duration, dy_sum / duration


class KXScrollView(Widget):
    '''
    Main differences from :class:`kivy.uix.scrollview.ScrollView`:

    * When :attr:`do_scroll_x` is False, the content's x position can be controlled via ``pos_hint``.
    * When :attr:`do_scroll_y` is False, the content's y position can be controlled via ``pos_hint``.
    * Nested instances work as expected, avoiding many of the issues present in the original.
    * The content can be scrolled even when it's smaller than the KXScrollView.
    '''
    scroll_distance = NumericProperty(SV.scroll_distance.defaultvalue)
    ''' :attr:`kivy.uix.scrollview.ScrollView.scroll_distance` '''

    scroll_timeout = NumericProperty(0.2)
    ''' :attr:`kivy.uix.scrollview.ScrollView.scroll_timeout` but in seconds'''

    scroll_wheel_distance = NumericProperty(SV.scroll_wheel_distance.defaultvalue)
    ''' :attr:`kivy.uix.scrollview.ScrollView.scroll_wheel_distance` '''

    smooth_scroll_end = NumericProperty(SV.smooth_scroll_end.defaultvalue, allownone=True)
    ''' :attr:`kivy.uix.scrollview.ScrollView.smooth_scroll_end` '''

    do_scroll_x = BooleanProperty(SV.do_scroll_x.defaultvalue)
    ''' :attr:`kivy.uix.scrollview.ScrollView.do_scroll_x` '''

    do_scroll_y = BooleanProperty(SV.do_scroll_y.defaultvalue)
    ''' :attr:`kivy.uix.scrollview.ScrollView.do_scroll_y` '''

    do_overscroll_x = BooleanProperty(True)

    do_overscroll_y = BooleanProperty(True)

    content = ObjectProperty(None, allownone=True)
    '''(read-only)'''

    content_x = NumericProperty()
    '''(read-only) The X position of the content relative to the KXScrollView.'''

    content_y = NumericProperty()
    '''(read-only) The Y position of the content relative to the KXScrollView.'''

    content_pos = ReferenceListProperty(content_x, content_y)
    '''(read-only) A ``ReferenceListProperty`` of (``content_x`` and ``content_y``) properties.'''

    content_min_x = NumericProperty()
    '''(read-only) The lower bound of the content's X position relative to the KXScrollView.'''

    content_min_y = NumericProperty()
    '''(read-only) The lower bound of the content's Y position relative to the KXScrollView.'''

    content_max_x = NumericProperty()
    '''(read-only) The higher bound of the content's X position relative to the KXScrollView.'''

    content_max_y = NumericProperty()
    '''(read-only) The higher bound of the content's Y position relative to the KXScrollView.'''

    # These can be unfinalized values that may exceed the bounds even if
    # `do_overscroll_x` and `do_overscroll_y`` are False.
    _content_x = NumericProperty()
    _content_y = NumericProperty()

    effect_x = ObjectProperty(None, allownone=True)
    '''
    Effect to apply for the X axis. If None is set, KXScrollView internally
    creates an appropriate instance with the following rules:

    * If :attr:`do_overscroll_x` is True, it creates a :class:`KXDampedScrollEffect`.
    * If :attr:`do_overscroll_x` is False, it creates a :class:`KXScrollEffect`.

    You may want to set this to non-None when:

    * You want to use a custom effect.
    * You want to use an existing effect but with a different configuration.
    '''

    effect_y = ObjectProperty(None, allownone=True)

    hbar_enabled = BooleanProperty(False)
    hbar_length_min = NumericProperty("10dp")
    hbar_thickness = NumericProperty("10dp")
    hbar_x = NumericProperty()
    '''(read-only) The X position of the horizontal scrollbar relative to the KXScrollView.'''

    hbar_y = NumericProperty()
    '''
    The Y position of the horizontal scrollbar relative to the KXScrollView.

    By default, the horizontal scrollbar is placed at the bottom of the KXScrollView.
    To move it to the top, do the following:

    .. code-block:: yaml

        KXScrollView:
            hbar_y: self.height - self.hbar_thickness
    '''

    hbar_color = ColorProperty("#CCCCCC77")
    _hbar_length = NumericProperty()
    _content2hbar_ratio = NumericProperty(1.)
    '''
    Represents how many pixels the horizontal scroll bar moves in response to a 1-pixel horizontal
    movement of the ScrollView content.
    '''

    vbar_enabled = BooleanProperty(False)
    vbar_length_min = NumericProperty("10dp")
    vbar_thickness = NumericProperty("10dp")
    vbar_x = NumericProperty()
    '''
    The X position of the vertical scrollbar relative to the KXScrollView.

    By default, the vertical scrollbar is placed on the left side of the KXScrollView.  
    To move it to the right, do the following:

    .. code-block:: yaml

        KXScrollView:
            vbar_x: self.width - self.vbar_thickness
    '''

    vbar_y = NumericProperty()
    '''(read-only) The Y position of the vertical scrollbar relative to the KXScrollView.'''

    vbar_color = ColorProperty("#CCCCCC77")
    _vbar_length = NumericProperty()
    _content2vbar_ratio = NumericProperty(1.)
    '''
    Represents how many pixels the vertical scroll bar moves in response to a 1-pixel vertical
    movement of the ScrollView content.
    '''

    def __init__(self, **kwargs):
        self._main_task = ak.dummy_task
        self._effect_x = self._effect_y = None
        self._prev_content = None
        super().__init__(**kwargs)
        f = self.fbind

        t = Clock.schedule_once(self._reset, -1)
        f("disabled", t)
        f("children", t)
        f("effect_x", t)
        f("effect_y", t)
        f("do_scroll_x", t)
        f("do_scroll_y", t)
        f("do_overscroll_x", t)
        f("do_overscroll_y", t)
        f("hbar_enabled", t)
        f("vbar_enabled", t)

    def _reset(self, dt):
        self._main_task.cancel()
        if self.disabled:
            return
        self._main_task = ak.managed_start(self._main())

    def to_local(self, x, y, **k):
        cx, cy = self.content_pos
        sx, sy = self.pos
        return x - cx - sx, y - cy - sy

    def to_parent(self, x, y, **k):
        cx, cy = self.content_pos
        sx, sy = self.pos
        return x + cx + sx, y + cy + sy

    def _apply_transform(self, m, pos=None):
        cx, cy = self.content_pos
        sx, sy = self.pos
        m.translate(cx + sx, cy + sy, 0)
        return super()._apply_transform(m, (0, 0))

    def on_motion(self, etype, me):
        if me.type_id in self.motion_filter and 'pos' in me.profile:
            me.push()
            me.apply_transform_2d(self.to_local)
            ret = super().on_motion(etype, me)
            me.pop()
            return ret
        return super().on_motion(etype, me)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.opos):
            touch.push()
            touch.apply_transform_2d(self.to_local)
            super().on_touch_down(touch)
            touch.pop()
            return True

    def on_touch_move(self, touch):
        if self.collide_point(*touch.pos):
            touch.push()
            touch.apply_transform_2d(self.to_local)
            super().on_touch_move(touch)
            touch.pop()
            return True

    def on_touch_up(self, touch):
        if self.collide_point(*touch.pos):
            touch.push()
            touch.apply_transform_2d(self.to_local)
            super().on_touch_up(touch)
            touch.pop()
            return True

    def stop_scroll_momentum(self):
        if (e := self._effect_x) is not None:
            e.deactivate()
            e.velocity = 0
        if (e := self._effect_y) is not None:
            e.deactivate()
            e.velocity = 0

    def scroll_by_distance(self, x=None, y=None):
        '''Adjust the momentum to achieve a specified scroll distance.'''
        if x is not None and (e := self._effect_x) is not None:
            e.scroll_by(x)
            e.activate()
        if y is not None and (e := self._effect_y) is not None:
            e.scroll_by(y)
            e.activate()

    def scroll_to_pos(self, x=None, y=None):
        '''Adjust the momentum to reach a specified scroll position.'''
        if x is not None and (e := self._effect_x) is not None:
            e.scroll_to(x)
            e.activate()
        if y is not None and (e := self._effect_y) is not None:
            e.scroll_to(y)
            e.activate()

    def scroll_to_widget(self, widget):
        '''
        Adjust the momentum to scroll until a specified widget is visible.

        :param widget: This must be a child or descendant of the :attr:`content`.
        '''
        content = self.content
        parent = widget.parent
        cx, cy = widget.center
        try:
            while parent is not content:
                parent = parent.parent
                cx, cy = parent.to_parent(cx, cy)
        except AttributeError:  # The Window obejct doesn't have a 'to_parent' method.
            raise ValueError(f"{widget} is not a child or descendant of the KXScrollView content.")
        w, h = self.size
        self.scroll_to_pos(w * 0.5 - cx, h * 0.5 - cy)

    @contextmanager
    def _sync_with_effect_x(self, sync_attr=ak.sync_attr):
        e = self.effect_x
        if e is None:
            if self.do_overscroll_x:
                e = KXDampedScrollEffect()
            else:
                e = KXScrollEffect()
        e.activate()
        e.velocity = 0
        e.min = self.content_min_x
        e.max = self.content_max_x
        e.value = self.content_x
        self._effect_x = e
        try:
            with (
                sync_attr((self, "content_x"), (e, "value")),
                sync_attr((e, "value"), (self, "content_x")),
                sync_attr((self, "content_min_x"), (e, "min")),
                sync_attr((self, "content_max_x"), (e, "max")),
            ):
                yield
        finally:
            e.deactivate()
            self._effect_x = None

    @contextmanager
    def _sync_with_effect_y(self, sync_attr=ak.sync_attr):
        e = self.effect_y
        if e is None:
            if self.do_overscroll_y:
                e = KXDampedScrollEffect()
            else:
                e = KXScrollEffect()
        e.activate()
        e.velocity = 0
        e.min = self.content_min_y
        e.max = self.content_max_y
        e.value = self.content_y
        self._effect_y = e
        try:
            with (
                sync_attr((self, "content_y"), (e, "value")),
                sync_attr((e, "value"), (self, "content_y")),
                sync_attr((self, "content_min_y"), (e, "min")),
                sync_attr((self, "content_max_y"), (e, "max")),
            ):
                yield
        finally:
            e.deactivate()
            self._effect_y = None

    async def _main(self):
        children = self.children
        if not children:
            return
        if len(children) != 1:
            raise Exception("KXScrollView can only have one child")
        try:
            self._content2hbar_ratio = 1.
            self._content2vbar_ratio = 1.
            self._hbar_length = 0
            self._vbar_length = 0
            self.content = c = children[0]
            if self._prev_content is not c:
                c.pos = self.content_pos = (0, 0)
            with ExitStack() as stack:
                ec = stack.enter_context
                ec(self._keep_updating_content_size_from_hint(c))
                if self.do_scroll_x:
                    ec(self._sync_with_effect_x())
                    ec(self._keep_updating_bounds_x(c))
                    ec(self._keep_updating_content_x())
                    if self.hbar_enabled:
                        ec(self._keep_updating_hbar_length_and_ratio(c))
                        ec(self._keep_updating_hbar_x())
                else:
                    ec(self._keep_updating_content_x_from_hint(c))
                if self.do_scroll_y:
                    ec(self._sync_with_effect_y())
                    ec(self._keep_updating_bounds_y(c))
                    ec(self._keep_updating_content_y())
                    if self.vbar_enabled:
                        ec(self._keep_updating_vbar_length_and_ratio(c))
                        ec(self._keep_updating_vbar_y())
                else:
                    ec(self._keep_updating_content_y_from_hint(c))

                await self._root_touch_handler()
        finally:
            self._prev_content = c
            self.content = None

    def _is_colliding_with_hbar(self, x, y):
        return (self.hbar_x <= x < (self.hbar_x + self._hbar_length)) and \
            (self.hbar_y <= y < (self.hbar_y + self.hbar_thickness))

    def _is_colliding_with_vbar(self, x, y):
        return (self.vbar_x <= x < (self.vbar_x + self.vbar_thickness)) and \
            (self.vbar_y <= y < (self.vbar_y + self._vbar_length))

    async def _root_touch_handler(self):
        hbar_enabled = self.hbar_enabled and self.do_scroll_x
        vbar_enabled = self.vbar_enabled and self.do_scroll_y
        bar_enabled = hbar_enabled or vbar_enabled
        on_touch_down = partial(ak.event, self, "on_touch_down", filter=is_opos_colliding)
        handle_mouse_wheel = self._handle_mouse_wheel
        handle_potential_scrolling_gesture = self._handle_potential_scrolling_gesture
        handle_hbar_drag = self._handle_hbar_drag
        handle_vbar_drag = self._handle_vbar_drag
        is_colliding_with_hbar = self._is_colliding_with_hbar
        is_colliding_with_vbar = self._is_colliding_with_vbar

        while True:
            __, touch = await on_touch_down()
            if touch.is_mouse_scrolling:
                await handle_mouse_wheel(touch)
                continue
            if bar_enabled:
                x, y = touch.opos
                x -= self.x
                y -= self.y
                if vbar_enabled and is_colliding_with_vbar(x, y):
                    await handle_vbar_drag(touch)
                    continue
                if hbar_enabled and is_colliding_with_hbar(x, y):
                    await handle_hbar_drag(touch)
                    continue
            await handle_potential_scrolling_gesture(touch)

    _on_touch_up = partial(ak.event, Window, "on_touch_up")

    async def _handle_mouse_wheel(self, touch, VERTICAL_DIRECTIONS=("up", "down"),
                                     POSITIVE_DIRECTIONS=("up", "right")):
        # STEP1: Check if scrolling is necessary or allowed in a given direction.
        direction = touch.button[6:]  # len("scroll") == 6
        is_vertical = direction in VERTICAL_DIRECTIONS
        if is_vertical:
            if not self.do_scroll_y:
                return
            pos = self.content_y
            pos_min = self.content_min_y
            pos_max = self.content_max_y
        else:
            if not self.do_scroll_x:
                return
            pos = self.content_x
            pos_min = self.content_min_x
            pos_max = self.content_max_x
        is_positive = direction in POSITIVE_DIRECTIONS
        if is_positive and pos_max > pos:
            pass
        elif (not is_positive) and pos_min < pos:
            pass
        else:
            return

        # STEP2: Check if the scrollview should handle this touch.
        claim_signal = touch.ud["kivyx_claim_signal"]
        tasks = await ak.wait_any(
            claim_signal.wait(),
            self._on_touch_up(filter=lambda w, t, touch=touch: t is touch),
        )
        if tasks[0].finished:
            # Someone else took the touch so we withraw from it.
            return
        # We handle the touch.
        claim_signal.fire()

        # STEP3: Apply the mouse wheel scroll.
        d = self.scroll_wheel_distance
        d = d if is_positive else -d
        smooth = self.smooth_scroll_end
        if smooth is None:
            self.stop_scroll_momentum()
            pos += d
            if is_vertical:
                self._content_y = pos
            else:
                self._content_x = pos
        else:
            e = self._effect_y if is_vertical else self._effect_x
            e.velocity += d * smooth
            e.activate()

    async def _handle_potential_scrolling_gesture(self, touch, abs=abs, ak=ak):
        claim_signal = touch.ud["kivyx_claim_signal"]
        dx_sum = dy_sum = 0.
        scroll_distance = self.scroll_distance
        do_scroll_x = self.do_scroll_x
        do_scroll_y = self.do_scroll_y
        do_overscroll_x = self.do_overscroll_x
        do_overscroll_y = self.do_overscroll_y
        touch_history = deque(maxlen=5); history_append = touch_history.append
        history_append((touch.time_start, 0, 0))

        def is_the_same_touch(w, t, touch=touch):
            # Needs to check if 't.grab_current' is None because 'on_touch_move' events are doubled
            # when the 'touchring' module is active. (Grabbed one and non-grabbed one).
            return t is touch and t.grab_current is None

        async with (
            ak.event_freq(Window, "on_touch_move", filter=is_the_same_touch) as on_touch_move,
            ak.move_on_when(ak.wait_any(
                claim_signal.wait(),
                self._on_touch_up(filter=is_the_same_touch),
                ak.sleep(self.scroll_timeout),
            )) as cancel_tracker,
        ):
            while True:
                await on_touch_move()
                dx = touch.dx
                dy = touch.dy
                dx_sum += dx
                dy_sum += dy
                history_append((touch.time_update, dx, dy))
                if do_scroll_y and abs(dy_sum) > scroll_distance:
                    if do_overscroll_y:
                        break
                    if dy_sum > 0 and self.content_y < self.content_max_y:
                        break
                    if dy_sum < 0 and self.content_y > self.content_min_y:
                        break
                elif do_scroll_x and abs(dx_sum) > scroll_distance:
                    if do_overscroll_x:
                        break
                    if dx_sum > 0 and self.content_x < self.content_max_x:
                        break
                    if dx_sum < 0 and self.content_x > self.content_min_x:
                        break
        if cancel_tracker.finished:
            # We withdraw from the touch. The reason can be any of the following:
            # * Someone else took the touch.
            # * The touch didn't travel far enough within a time limit.
            # * The touch ended before it traveled far enough.
            return

        # The touch is confirmed as a scrolling gesture we should handle.
        claim_signal.fire()

        self.stop_scroll_momentum()

        # Apply the distance already traveled.
        if do_scroll_y:
            self._content_y += dy_sum
        if do_scroll_x:
            self._content_x += dx_sum

        # Move the content along with the touch.
        async with (
            ak.event_freq(Window, "on_touch_move", filter=is_the_same_touch) as on_touch_move,
            ak.move_on_when(self._on_touch_up(filter=is_the_same_touch)),
        ):
            while True:
                await on_touch_move()
                dx = touch.dx
                dy = touch.dy
                history_append((touch.time_update, dx, dy))
                if do_scroll_y:
                    self._content_y += dy
                if do_scroll_x:
                    self._content_x += dx
        history_append((touch.time_end, 0, 0))

        # The touch ended. Activate the effect.
        vel_x, vel_y = compute_velocity(touch_history)
        if do_scroll_y:
            e = self._effect_y
            e.velocity = vel_y
            e.activate()
        if do_scroll_x:
            e = self._effect_x
            e.velocity = vel_x
            e.activate()

    async def _handle_hbar_drag(self, touch):
        claim_signal = touch.ud["kivyx_claim_signal"]
        if claim_signal.is_fired:
            return
        claim_signal.fire()
        self.stop_scroll_momentum()
        hbar2content_ratio = 1. / self._content2hbar_ratio

        def is_the_same_touch(w, t, touch=touch):
            # Needs to check if 't.grab_current' is None because 'on_touch_move' events are doubled
            # when the 'touchring' module is active. (Grabbed one and non-grabbed one).
            return t.grab_current is None and t is touch

        # Move the content along with the touch.
        async with (
            ak.move_on_when(self._on_touch_up(filter=is_the_same_touch)),
            ak.event_freq(Window, "on_touch_move", filter=is_the_same_touch) as on_touch_move,
        ):
            while True:
                await on_touch_move()
                self._content_x += touch.dx * hbar2content_ratio

        self._effect_x.activate()

    async def _handle_vbar_drag(self, touch):
        claim_signal = touch.ud["kivyx_claim_signal"]
        if claim_signal.is_fired:
            return
        claim_signal.fire()
        self.stop_scroll_momentum()
        vbar2content_ratio = 1. / self._content2vbar_ratio

        def is_the_same_touch(w, t, touch=touch):
            # Needs to check if 't.grab_current' is None because 'on_touch_move' events are doubled
            # when the 'touchring' module is active. (Grabbed one and non-grabbed one).
            return t.grab_current is None and t is touch

        # Move the content along with the touch.
        async with (
            ak.move_on_when(self._on_touch_up(filter=is_the_same_touch)),
            ak.event_freq(Window, "on_touch_move", filter=is_the_same_touch) as on_touch_move,
        ):
            while True:
                await on_touch_move()
                self._content_y += touch.dy * vbar2content_ratio

        self._effect_y.activate()
        
    def _update_bounds_x(self, *__):
        diff = self.width - self.content.width
        if diff < 0:
            self.content_min_x = diff
            self.content_max_x = 0
        else:
            self.content_min_x = 0
            self.content_max_x = diff

    @contextmanager
    def _keep_updating_bounds_x(self, content):
        f = self._update_bounds_x
        f()
        try:
            content.bind(width=f)
            self.bind(width=f)
            yield
        finally:
            content.unbind(width=f)
            self.unbind(width=f)

    def _update_bounds_y(self, *__):
        diff = self.height - self.content.height
        if diff < 0:
            self.content_min_y = diff
            self.content_max_y = 0
        else:
            self.content_min_y = 0
            self.content_max_y = diff

    @contextmanager
    def _keep_updating_bounds_y(self, content):
        f = self._update_bounds_y
        f()
        try:
            content.bind(height=f)
            self.bind(height=f)
            yield
        finally:
            content.unbind(height=f)
            self.unbind(height=f)

    def _clamp_content_x(self, dt, clamp=clamp):
        self.content_x = self._content_x = clamp(self._content_x, self.content_min_x, self.content_max_x)
        return False

    @contextmanager
    def _keep_updating_content_x(self):
        if self.do_overscroll_x:
            with ak.sync_attr((self, "_content_x"), (self, "content_x")):
                yield
        else:
            t = Clock.create_trigger(self._clamp_content_x, -1, interval=True)
            try:
                self.bind(_content_x=t, content_min_x=t, content_max_x=t)
                yield
            finally:
                t.cancel()
                self.unbind(_content_x=t, content_min_x=t, content_max_x=t)

    def _clamp_content_y(self, dt, clamp=clamp):
        self.content_y = self._content_y = clamp(self._content_y, self.content_min_y, self.content_max_y)
        return False

    @contextmanager
    def _keep_updating_content_y(self):
        if self.do_overscroll_y:
            with ak.sync_attr((self, "_content_y"), (self, "content_y")):
                yield
        else:
            t = Clock.create_trigger(self._clamp_content_y, -1, interval=True)
            try:
                self.bind(_content_y=t, content_min_y=t, content_max_y=t)
                yield
            finally:
                t.cancel()
                self.unbind(_content_y=t, content_min_y=t, content_max_y=t)

    def _update_content_size_from_hint(self, dt, max=max, min=min):
        c = self.content
        if (hint := c.size_hint_x) is not None:
            w = hint * self.width
            if (hint := c.size_hint_min_x) is not None:
                w = max(w, hint)
            if (hint := c.size_hint_max_x) is not None:
                w = min(w, hint)
            c.width = w
        if (hint := c.size_hint_y) is not None:
            h = hint * self.height
            if (hint := c.size_hint_min_y) is not None:
                h = max(h, hint)
            if (hint := c.size_hint_max_y) is not None:
                h = min(h, hint)
            c.height = h

    @contextmanager
    def _keep_updating_content_size_from_hint(self, content):
        t = Clock.schedule_once(self._update_content_size_from_hint, -1)
        try:
            content.bind(size_hint_x=t, size_hint_min_x=t, size_hint_max_x=t,
                         size_hint_y=t, size_hint_min_y=t, size_hint_max_y=t)
            self.bind(width=t, height=t)
            yield
        finally:
            t.cancel()
            content.unbind(size_hint_x=t, size_hint_min_x=t, size_hint_max_x=t,
                           size_hint_y=t, size_hint_min_y=t, size_hint_max_y=t)
            self.unbind(width=t, height=t)

    def _update_content_x_from_hint(self, dt):
        c = self.content
        get_hint = c.pos_hint.get
        if (hint := get_hint("x")) is not None:
            x = hint * self.width
        elif (hint := get_hint("right")) is not None:
            x = hint * self.width - c.width
        elif (hint := get_hint("center_x")) is not None:
            x = hint * self.width - c.width / 2.
        elif (hint := get_hint("center")) is not None:
            x = hint[0] * self.width - c.width / 2.
        elif (hint := get_hint("pos")) is not None:
            x = hint[0] * self.width
        else:
            return
        self.content_x = x

    @contextmanager
    def _keep_updating_content_x_from_hint(self, content):
        t = Clock.schedule_once(self._update_content_x_from_hint, -1)
        try:
            content.bind(pos_hint=t, width=t)
            self.bind(width=t)
            yield
        finally:
            t.cancel()
            content.unbind(pos_hint=t, width=t)
            self.unbind(width=t)

    def _update_content_y_from_hint(self, dt):
        c = self.content
        get_hint = c.pos_hint.get
        if (hint := get_hint("y")) is not None:
            y = hint * self.height
        elif (hint := get_hint("top")) is not None:
            y = hint * self.height - c.height
        elif (hint := get_hint("center_y")) is not None:
            y = hint * self.height - c.height / 2.
        elif (hint := get_hint("center")) is not None:
            y = hint[1] * self.height - c.height / 2.
        elif (hint := get_hint("pos")) is not None:
            y = hint[1] * self.height
        else:
            return
        self.content_y = y

    @contextmanager
    def _keep_updating_content_y_from_hint(self, content):
        t = Clock.schedule_once(self._update_content_y_from_hint, -1)
        try:
            content.bind(pos_hint=t, height=t)
            self.bind(height=t)
            yield
        finally:
            t.cancel()
            content.unbind(pos_hint=t, height=t)
            self.unbind(height=t)

    def _update_hbar_length_and_ratio(self, dt, max=max):
        self_width = self.width
        w = self.content.width

        scrollable_width = self_width - w
        if not scrollable_width:
            self._hbar_length = 0
            self._content2hbar_ratio = 1.
            return
        if scrollable_width < 0:
            hbar_length = self_width / w * self_width
        else:
            hbar_length = w
        hbar_length = max(hbar_length, self.hbar_length_min)
        self._hbar_length = hbar_length
        self._content2hbar_ratio = (self_width - hbar_length) / scrollable_width

    @contextmanager
    def _keep_updating_hbar_length_and_ratio(self, content):
        t = Clock.schedule_once(self._update_hbar_length_and_ratio, -1)
        try:
            self.bind(width=t, hbar_length_min=t)
            content.bind(width=t)
            yield
        finally:
            t.cancel()
            self.unbind(width=t, hbar_length_min=t)
            content.unbind(width=t)

    def _update_vbar_length_and_ratio(self, dt, max=max):
        self_height = self.height
        h = self.content.height

        scrollable_height = self_height - h
        if not scrollable_height:
            self._vbar_length = 0
            self._content2vbar_ratio = 1.
            return
        if scrollable_height < 0:
            vbar_length = self_height / h * self_height
        else:
            vbar_length = h
        vbar_length = max(vbar_length, self.vbar_length_min)
        self._vbar_length = vbar_length
        self._content2vbar_ratio = (self_height - vbar_length) / scrollable_height

    @contextmanager
    def _keep_updating_vbar_length_and_ratio(self, content):
        t = Clock.schedule_once(self._update_vbar_length_and_ratio, -1)
        try:
            self.bind(height=t, vbar_length_min=t)
            content.bind(height=t)
            yield
        finally:
            t.cancel()
            self.unbind(height=t, vbar_length_min=t)
            content.unbind(height=t)

    def _update_hbar_x(self, *__):
        self.hbar_x = self.content_x * self._content2hbar_ratio

    @contextmanager
    def _keep_updating_hbar_x(self):
        f = self._update_hbar_x
        try:
            self.bind(content_x=f, _content2hbar_ratio=f)
            yield
        finally:
            self.unbind(content_x=f, _content2hbar_ratio=f)

    def _update_vbar_y(self, *__):
        self.vbar_y = self.content_y * self._content2vbar_ratio

    @contextmanager
    def _keep_updating_vbar_y(self):
        f = self._update_vbar_y
        try:
            self.bind(content_y=f, _content2vbar_ratio=f)
            yield
        finally:
            self.unbind(content_y=f, _content2vbar_ratio=f)
