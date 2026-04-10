__all__ = ("enable_touch_ring", "generate_ring_texture", )

from collections.abc import Sequence
from functools import partial
import math

from kivy.utils import get_color_from_hex
from kivy.graphics import (
    Fbo, Color, Line, ClearColor, ClearBuffers, Rectangle, InstructionGroup, PushMatrix, PopMatrix, Scale,
)
from kivy.graphics.texture import Texture
from kivy.core.window import Window
import asynckivy as ak


def generate_ring_texture(*, size=256, thickness=3, color: Sequence[float] | str=(1, 1, 1, 1)):
    '''
    Generates and returns a ring texture.

    :param size:
        The size of the texture in pixels (the texture will be square). Defaults to ``256``.
    :param thickness:
        The thickness of the ring in pixels. Defaults to ``3``.
    :param color:
        The color of the ring. Can be a sequence of RGBA values or a hex string. Defaults to ``(1, 1, 1, 1)``.
    '''
    if isinstance(color, str):
        color = get_color_from_hex(color)
    ig = InstructionGroup()
    for inst in (
         ClearColor(0, 0, 0, 0),
         ClearBuffers(),
         Color(*color),
         Line(circle=(size / 2, size / 2, size / 2 - thickness), width=thickness),
    ):
        ig.add(inst)
    tex = Texture.create(size=(size, size))

    def restore(tex, ig=ig):
        fbo = Fbo(texture=tex)
        fbo.add(ig)
        fbo.draw()
        fbo.remove(ig)
    restore(tex)
    tex.add_reload_observer(restore)
    return tex


async def enable_touch_ring(
    *, size=128, thickness=3, color: Sequence[float] | str=(1, 1, 1, 1),
    pulse=False, pulse_amplitude=.1, pulse_frequency=4.0,
):
    '''
    Shows rings around each touch on the screen until the returned coroutine is cancelled.

    :param size:
        The diameter of the rings in pixels. Defaults to ``128``.
    :param thickness:
        The thickness of the rings in pixels. Defaults to ``3``.
    :param color:
        The color of the rings. Can be a sequence of RGBA values or a hex string.
        Defaults to ``(1, 1, 1, 1)``. (Currently, there is a bug where setting the alpha value
        to less than 1 causes squares to be displayed instead of circles. )
    :param pulse:
        Whether the rings should pulse. Defaults to ``False``.
    :param pulse_amplitude:
        The amplitude of the pulsing effect. Defaults to ``.1``,
        meaning the rings will grow and shrink by 10% of their original size.
    :param pulse_frequency:
        The frequency of the pulsing effect. Defaults to ``4.0``,
        meaning the rings will complete 4 full pulses per second.
    '''
    ring_texture = generate_ring_texture(size=size, thickness=thickness, color=color)

    async with ak.open_nursery() as nursery:
        def on_touch_xxx(
            window, touch,
            seen="kivyx.touchring",
            start=nursery.start,
            show_ring=partial(_show_pulsing_ring, ring_texture, pulse_amplitude, pulse_frequency) \
                if pulse else partial(_show_ring, ring_texture),
        ):
            if seen in touch.ud:
                return
            touch.ud[seen] = True
            if touch.is_mouse_scrolling:
                return
            start(show_ring(window, touch))

        Window.bind(on_touch_down=on_touch_xxx, on_touch_move=on_touch_xxx)
        try:
            await ak.sleep_forever()
        finally:
            Window.unbind(on_touch_down=on_touch_xxx, on_touch_move=on_touch_xxx)


async def _show_ring(ring_texture, window, touch):
    tex_size = ring_texture.size
    offset_x = -tex_size[0] / 2
    offset_y = -tex_size[1] / 2
    ig = InstructionGroup()
    ig.add(Color())
    ig.add(rect := Rectangle(
        texture=ring_texture,
        pos=(touch.x + offset_x, touch.y + offset_y),
        size=tex_size,
    ))

    def is_the_same_touch(w, t, touch=touch):
        return t is touch
    window.canvas.after.add(ig)
    try:
        async with (
            # When this function is called from a `Window.on_touch_down` event,
            # `touch.ud["kivyx_end"]` is not yet available.
            ak.move_on_when(ak.event(window, "on_touch_up", filter=is_the_same_touch)),
            ak.event_freq(window, "on_touch_move", filter=is_the_same_touch) as on_touch_move,
        ):
            while True:
                await on_touch_move()
                rect.pos = (touch.x + offset_x, touch.y + offset_y)
    finally:
        window.canvas.after.remove(ig)


async def _show_pulsing_ring(ring_texture, pulse_amplitude, pulse_frequency, window, touch):
    tex_size = ring_texture.size
    offset_x = -tex_size[0] / 2
    offset_y = -tex_size[1] / 2
    ig = InstructionGroup()
    ig.add(PushMatrix())
    ig.add(scale := Scale(origin=touch.pos))
    ig.add(Color())
    ig.add(rect := Rectangle(
        texture=ring_texture,
        pos=(touch.x + offset_x, touch.y + offset_y),
        size=tex_size,
    ))
    ig.add(PopMatrix())

    def is_the_same_touch(w, t, touch=touch):
        return t is touch
    window.canvas.after.add(ig)
    try:
        async with (
            # When this function is called from a `Window.on_touch_down` event,
            # `touch.ud["kivyx_end"]` is not yet available.
            ak.move_on_when_any(
                ak.event(window, "on_touch_up", filter=is_the_same_touch),
                _pulse(scale, pulse_amplitude, pulse_frequency),
            ),
            ak.event_freq(window, "on_touch_move", filter=is_the_same_touch) as on_touch_move,
        ):
            while True:
                await on_touch_move()
                rect.pos = (touch.x + offset_x, touch.y + offset_y)
                scale.origin = touch.pos
    finally:
        window.canvas.after.remove(ig)


async def _pulse(scale: Scale, amplitude: float, frequency: float):
    sin = math.sin
    elapsed_time = 0.
    time_coeff = math.tau * frequency
    async with ak.sleep_freq() as sleep:
        while True:
            elapsed_time += await sleep()
            s = amplitude * sin(elapsed_time * time_coeff) + 1.0
            scale.xyz = (s, s, 1.0)
