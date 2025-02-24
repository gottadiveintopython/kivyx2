__all__ = ('KXScrollEffect', )
from typing import Self
from functools import partial

from kivy.clock import Clock
from kivy.event import EventDispatcher
from kivy.properties import NumericProperty


class KXScrollEffect(EventDispatcher):
    ''' A :class:`~kivy.effects.scroll.ScrollEffect` equivalence. '''

    value = NumericProperty(0)
    ''' :attr:`kivy.effects.kinetic.KineticEffect.value` '''

    min = NumericProperty(0)
    ''' :attr:`kivy.effects.scroll.ScrollEffect.min` '''

    max = NumericProperty(0)
    ''' :attr:`kivy.effects.scroll.ScrollEffect.max` '''

    velocity = NumericProperty(0)
    ''' :attr:`kivy.effects.kinetic.KineticEffect.velocity` '''

    min_velocity = NumericProperty(16.0)
    ''' :attr:`kivy.effects.kinetic.KineticEffect.min_velocity` '''

    friction = NumericProperty(0.05)
    ''' :attr:`kivy.effects.kinetic.KineticEffect.friction` '''

    std_dt = NumericProperty(0.017)
    ''' :attr:`kivy.effects.kinetic.KineticEffect.std_dt` '''

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        t = self._trigger_update = Clock.create_trigger(lambda dt: None, 0, True)
        self.activate = t
        self.deactivate = t.cancel
        t = Clock.schedule_once(self._update_params, -1)
        self.bind(min_velocity=t, friction=t, std_dt=t)

    def _update_params(self, dt):
        self._trigger_update.callback = partial(self._update, self.min_velocity, self.friction / self.std_dt, self)

    def _update(abs, min_velocity, friction_divided_by_std_dt, self: Self, dt):
        value = self.value
        min = self.min
        max = self.max
        velocity = self.velocity

        try:
            total_force = velocity * friction_divided_by_std_dt * dt
            velocity -= total_force
            value += velocity * dt

            if value < min:
                velocity = 0
                value = min
                return False
            elif value > max:
                velocity = 0
                value = max
                return False
            elif abs(velocity) <= min_velocity:
                velocity = 0
                return False
        finally:
            self.value = value
            self.velocity = velocity

    _update = partial(_update, abs)

    def scroll_by(self, distance):
        ''' Adjust the :attr:`velocity` to achieve a specified movement distance. '''
        self.velocity = distance * self.friction / self.std_dt

    def scroll_to(self, new_value):
        '''Adjust the :attr:`velocity` to reach a specified value.'''
        self.scroll_by(new_value - self.value)
