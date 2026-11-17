__all__ = ("KXSimpleScrollView", )

from functools import partial
from contextlib import contextmanager, ExitStack

from kivy.lang import Builder
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, BooleanProperty, ObjectProperty, ReferenceListProperty, ColorProperty, OptionProperty
import asynckivy as ak

from kivyx.utils import noop
from kivyx.touch_filters import is_opos_colliding

VERTICAL_DIRECTIONS = ("up", "down")
POSITIVE_DIRECTIONS = ("up", "right")

Builder.load_string('''
<KXSimpleScrollView>:
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
            size: self.hbar_length, self.hbar_thickness
            pos: self.hbar_x, self.hbar_y
        Color:
            rgba: self.vbar_color
        Rectangle:
            size: self.vbar_thickness, self.vbar_length
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


class KXSimpleScrollView(Widget):
    '''
    * No overscrolling.
    * No bounce effect.
    * No inertia (scrolling stops immediately when the finger is lifted).
    * No scroll wheel acceleration (scroll wheel input is converted to distance rather than velocity).
    '''

    scroll_wheel_distance = NumericProperty("100dp")
    ''' :attr:`kivy.uix.scrollview.ScrollView.scroll_wheel_distance` '''

    do_scroll_x = BooleanProperty(True)
    ''' :attr:`kivy.uix.scrollview.ScrollView.do_scroll_x` '''

    do_scroll_y = BooleanProperty(True)
    ''' :attr:`kivy.uix.scrollview.ScrollView.do_scroll_y` '''

    anchor_x = OptionProperty("left", options=("left", "right"))

    anchor_y = OptionProperty("top", options=("bottom", "top"))

    content = ObjectProperty(None, allownone=True)
    '''(read-only)'''

    content_x = NumericProperty()
    '''(read-only) The X position of the content relative to the KXScrollView.'''

    content_y = NumericProperty()
    '''(read-only) The Y position of the content relative to the KXScrollView.'''

    content_pos = ReferenceListProperty(content_x, content_y)
    '''(read-only) A :class:`~kivy.properties.ReferenceListProperty` of
    (:attr:`content_x` and :attr:`content_y`) properties.
    '''

    content_min_x = NumericProperty()
    '''(read-only) The lower bound of the content's X position relative to the KXScrollView.'''

    content_min_y = NumericProperty()
    '''(read-only) The lower bound of the content's Y position relative to the KXScrollView.'''

    content_max_x = NumericProperty()
    '''(read-only) The higher bound of the content's X position relative to the KXScrollView.'''

    content_max_y = NumericProperty()
    '''(read-only) The higher bound of the content's Y position relative to the KXScrollView.'''

    # These can be unfinalized values that may exceed the bounds.
    _content_x = NumericProperty()
    _content_y = NumericProperty()

    hbar_enabled = BooleanProperty(False)  #: ...
    hbar_length = NumericProperty()  #: (read-only)
    hbar_length_min = NumericProperty("10dp")  #: ...
    hbar_thickness = NumericProperty("10dp")  #: ...
    hbar_color = ColorProperty("#CCCCCC77")  #: ...

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

    _content2hbar_ratio = NumericProperty(1.)
    '''
    Represents how many pixels the horizontal scroll bar moves in response to a 1-pixel horizontal
    movement of the ScrollView content.
    '''

    vbar_enabled = BooleanProperty(False)  #: ...
    vbar_length = NumericProperty()  #: (read-only)
    vbar_length_min = NumericProperty("10dp")  #: ...
    vbar_thickness = NumericProperty("10dp")  #: ...
    vbar_color = ColorProperty("#CCCCCC77")  #: ...

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


    _content2vbar_ratio = NumericProperty(1.)
    '''
    Represents how many pixels the vertical scroll bar moves in response to a 1-pixel vertical
    movement of the ScrollView content.
    '''

    # Default values of instance attributes
    _deactivate = noop
    _prev_content = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        f = self.fbind
        t = Clock.schedule_once(self._reset, -1)
        f("disabled", t)
        f("children", t)
        f("do_scroll_x", t)
        f("do_scroll_y", t)
        f("hbar_enabled", t)
        f("vbar_enabled", t)
        f("anchor_x", t)
        f("anchor_y", t)

    def _reset(self, dt):
        self._deactivate()
        if self.disabled:
            return
        match len(self.children):
            case 0:
                self.content = None
                return
            case 1:
                pass
            case _:
                raise Exception("KXScrollView can only have one child")

        with ExitStack() as stack:
            defer = stack.callback
            ec = stack.enter_context

            self._content2hbar_ratio = 1.
            self._content2vbar_ratio = 1.
            self.hbar_length = 0.
            self.vbar_length = 0.
            self.content = c = self.children[0]
            defer(setattr, self, "_prev_content", c)

            if self._prev_content is not c:
                content_x = content_y = 0.
                if self.do_scroll_x and self.anchor_x == "right":
                    content_x = self.width - c.width
                if self.do_scroll_y and self.anchor_y == "top":
                    content_y = self.height - c.height
                self._content_x = content_x
                self._content_y = content_y

            ec(self._keep_updating_content_size_from_hint(c))
            if self.do_scroll_x:
                ec(self._keep_updating_bounds_x(c))
                ec(self._keep_updating_content_x())
                if self.anchor_x == "right":
                    ec(self._keep_adjusting_content_x_for_width_changes(c))
                if self.hbar_enabled:
                    ec(self._keep_updating_hbar_length_and_ratio(c))
                    ec(self._keep_updating_hbar_x())
            else:
                ec(self._keep_updating_content_x_from_hint(c))
            if self.do_scroll_y:
                ec(self._keep_updating_bounds_y(c))
                ec(self._keep_updating_content_y())
                if self.anchor_y == "top":
                    ec(self._keep_adjusting_content_y_for_height_changes(c))
                if self.vbar_enabled:
                    ec(self._keep_updating_vbar_length_and_ratio(c))
                    ec(self._keep_updating_vbar_y())
            else:
                ec(self._keep_updating_content_y_from_hint(c))

            defer(ak.start(self._root_touch_handler()).cancel)
            self._deactivate = stack.pop_all().close

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

    def cancel_user_scroll(self):
        '''Cancels ongoing user scroll if any.'''

    def _is_colliding_with_hbar(self, x, y):
        return (self.hbar_x <= x < (self.hbar_x + self.hbar_length)) and \
            (self.hbar_y <= y < (self.hbar_y + self.hbar_thickness))

    def _is_colliding_with_vbar(self, x, y):
        return (self.vbar_x <= x < (self.vbar_x + self.vbar_thickness)) and \
            (self.vbar_y <= y < (self.vbar_y + self.vbar_length))

    async def _root_touch_handler(self):
        hbar_enabled = self.hbar_enabled and self.do_scroll_x
        vbar_enabled = self.vbar_enabled and self.do_scroll_y
        bar_enabled = hbar_enabled or vbar_enabled
        on_touch_down = partial(ak.event, self, "on_touch_down", filter=is_opos_colliding)
        open_nursery = ak.open_nursery

        while True:
            __, touch = await on_touch_down()
            if touch.is_mouse_scrolling:
                await self._handle_mouse_wheel(touch)
                continue
            async with open_nursery() as nursery:
                nursery.start(touch.ud["kivyx_abandon"].wait(), daemon=True, close_on_finish=True)
                nursery.start(touch.ud["kivyx_touch_up"].wait(), daemon=True, close_on_finish=True)
                if bar_enabled:
                    x, y = touch.opos
                    x -= self.x
                    y -= self.y
                    if vbar_enabled and self._is_colliding_with_vbar(x, y):
                        await self._handle_potential_vbar_drag(touch)
                        continue
                    if hbar_enabled and self._is_colliding_with_hbar(x, y):
                        await self._handle_potential_hbar_drag(touch)
                        continue
                await self._handle_potential_scrolling_gesture(touch)

    async def _handle_mouse_wheel(self, touch):
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
        await touch.ud["kivyx_touch_up"].wait()
        ex_access = touch.ud["kivyx_exclusive_access"]
        if ex_access.has_been_claimed:
            return
        ex_access.claim("scroll", self)

        # STEP3: Apply the mouse wheel scroll.
        d = self.scroll_wheel_distance
        if is_positive:
            pos += d
        else:
            pos -= d
        if is_vertical:
            self._content_y = pos
        else:
            self._content_x = pos

    async def _handle_potential_scrolling_gesture(self, touch, ak=ak):
        ud = touch.ud
        ex_access = ud["kivyx_exclusive_access"]
        do_scroll_x = self.do_scroll_x
        do_scroll_y = self.do_scroll_y

        async with ak.open_nursery() as nursery:
            s = nursery.start
            s(ex_access.wait_for_someone_to_claim(), close_on_finish=True)
            if do_scroll_x:
                h_swipe_tracker = s(ud["kivyx_gestures"]["horizontal_swipe"].wait(), close_on_finish=True)
            if do_scroll_y:
                v_swipe_tracker = s(ud["kivyx_gestures"]["vertical_swipe"].wait(), close_on_finish=True)
        if ex_access.has_been_claimed:
            return

        # Check whether the swipe gesture would scroll beyond the content boundaries.
        total_dy = touch.y - touch.oy
        total_dx = touch.x - touch.ox
        if do_scroll_y and v_swipe_tracker.finished:
            if total_dy < 0. and self.content_y <= self.content_min_y:
                return
            if total_dy > 0. and self.content_y >= self.content_max_y:
                return
        elif do_scroll_x and h_swipe_tracker.finished:
            if total_dx < 0. and self.content_x <= self.content_min_x:
                return
            if total_dx > 0. and self.content_x >= self.content_max_x:
                return
        else:
            return

        ex_access.claim("scroll", self)
        self.cancel_user_scroll = ud["kivyx_abandon"].fire

        # Apply the distance already traveled.
        if do_scroll_y:
            self._content_y += total_dy
        if do_scroll_x:
            self._content_x += total_dx

        # Scroll the content along with the touch
        def is_the_same_touch(w, t, touch=touch):
            return t is touch
        with ak.event_freq(Window, "on_touch_move", filter=is_the_same_touch) as on_touch_move:
            while True:
                await on_touch_move()
                if do_scroll_y:
                    self._content_y += touch.dy
                if do_scroll_x:
                    self._content_x += touch.dx

    async def _handle_potential_hbar_drag(self, touch):
        # 内側にあるScrollViewを優先させたいので一旦待つ
        await touch.ud["kivyx_gestures"]["immediate"].wait()

        ex_access = touch.ud["kivyx_exclusive_access"]
        if ex_access.has_been_claimed:
            return
        ex_access.claim("scroll", self)
        self.cancel_user_scroll = touch.ud["kivyx_abandon"].fire

        # Move the content along with the touch.
        hbar2content_ratio = 1. / self._content2hbar_ratio
        with ak.event_freq(Window, "on_touch_move", filter=lambda w, t, touch=touch: t is touch) as on_touch_move:
            while True:
                await on_touch_move()
                self._content_x += touch.dx * hbar2content_ratio

    async def _handle_potential_vbar_drag(self, touch):
        # 内側にあるScrollViewを優先させたいので一旦待つ
        await touch.ud["kivyx_gestures"]["immediate"].wait()

        ex_access = touch.ud["kivyx_exclusive_access"]
        if ex_access.has_been_claimed:
            return
        ex_access.claim("scroll", self)
        self.cancel_user_scroll = touch.ud["kivyx_abandon"].fire

        # Move the content along with the touch.
        vbar2content_ratio = 1. / self._content2vbar_ratio
        with ak.event_freq(Window, "on_touch_move", filter=lambda w, t, touch=touch: t is touch) as on_touch_move:
            while True:
                await on_touch_move()
                self._content_y += touch.dy * vbar2content_ratio

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
            content.bind(size_hint=t, size_hint_min=t, size_hint_max=t)
            self.bind(width=t, height=t)
            yield
        finally:
            t.cancel()
            content.unbind(size_hint=t, size_hint_min=t, size_hint_max=t)
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
            self.hbar_length = 0
            self._content2hbar_ratio = 1.
            return
        if scrollable_width < 0:
            hbar_length = self_width / w * self_width
        else:
            hbar_length = w
        hbar_length = max(hbar_length, self.hbar_length_min)
        self.hbar_length = hbar_length
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
            self.vbar_length = 0
            self._content2vbar_ratio = 1.
            return
        if scrollable_height < 0:
            vbar_length = self_height / h * self_height
        else:
            vbar_length = h
        vbar_length = max(vbar_length, self.vbar_length_min)
        self.vbar_length = vbar_length
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

    def _adjust_content_x_for_width_changes(self, dt):
        prev_width = self._prev_width
        self._prev_width = cur_width = self.width
        prev_content_width = self._prev_content_width
        self._prev_content_width = cur_content_width = self.content.width
        self._content_x += cur_width - prev_width
        self._content_x -= cur_content_width - prev_content_width

    @contextmanager
    def _keep_adjusting_content_x_for_width_changes(self, content):
        self._prev_width = self.width
        self._prev_content_width = content.width
        t = Clock.create_trigger(self._adjust_content_x_for_width_changes, -1)
        try:
            self.bind(width=t)
            content.bind(width=t)
            yield
        finally:
            t.cancel()
            self.unbind(width=t)
            content.unbind(width=t)

    def _adjust_content_y_for_height_changes(self, dt):
        prev_height = self._prev_height
        self._prev_height = cur_height = self.height
        prev_content_height = self._prev_content_height
        self._prev_content_height = cur_content_height = self.content.height
        self._content_y += cur_height - prev_height
        self._content_y -= cur_content_height - prev_content_height

    @contextmanager
    def _keep_adjusting_content_y_for_height_changes(self, content):
        self._prev_height = self.height
        self._prev_content_height = content.height
        t = Clock.create_trigger(self._adjust_content_y_for_height_changes, -1)
        try:
            self.bind(height=t)
            content.bind(height=t)
            yield
        finally:
            t.cancel()
            self.unbind(height=t)
            content.unbind(height=t)
