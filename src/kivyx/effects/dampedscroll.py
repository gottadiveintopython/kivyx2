__all__ = ('KXDampedScrollEffect', )
from typing import Self
from functools import partial

from kivy.clock import Clock
from kivy.event import EventDispatcher
from kivy.properties import NumericProperty


class KXDampedScrollEffect(EventDispatcher):
    ''' A :class:`kivy.effects.damped.DampedScrollEffect` equivalence. '''

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

    min_overscroll = NumericProperty(1.0)
    ''' :attr:`kivy.effects.dampedscroll.DampedScrollEffect.min_overscroll` '''

    friction = NumericProperty(0.05)
    ''' :attr:`kivy.effects.kinetic.KineticEffect.friction` '''

    std_dt = NumericProperty(0.017)
    ''' :attr:`kivy.effects.kinetic.KineticEffect.std_dt` '''

    edge_damping = NumericProperty(0.25)
    ''' :attr:`kivy.effects.dampedscroll.DampedScrollEffect.edge_damping` '''

    spring_constant = NumericProperty(1.6)
    ''' :attr:`kivy.effects.dampedscroll.DampedScrollEffect.spring_constant` '''

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        t = self._trigger_update = Clock.create_trigger(lambda dt: None, 0, True)
        self.activate = t
        self.deactivate = t.cancel
        t = Clock.schedule_once(self._update_params, -1)
        self.bind(min_overscroll=t, min_velocity=t, friction=t, std_dt=t, edge_damping=t, spring_constant=t)

    def _update_params(self, dt):
        self._trigger_update.callback = partial(
            self._update, self.min_velocity, self.edge_damping, self.spring_constant, self.min_overscroll,
            self.friction / self.std_dt, self)

    def _update(
            abs, MAX, MIN,
            min_velocity, edge_damping, spring_constant, min_overscroll, friction_divided_by_std_dt,
            self: Self, dt):
        value = self.value
        min = self.min
        max = self.max
        velocity = self.velocity

        try:
            if value < min:
                overscroll = value - min
            elif value > max:
                overscroll = value - max
            else:
                overscroll = 0
                if abs(velocity) <= min_velocity and (not overscroll):
                    velocity = 0
                    return False

            total_force = velocity * friction_divided_by_std_dt * dt
            stop_too_much_bounce = None
            if abs(overscroll) > min_overscroll:
                total_force += velocity * edge_damping
                total_force += overscroll * spring_constant
            if overscroll > 0 and velocity < 0:
                stop_too_much_bounce = MAX
            elif overscroll < 0 and velocity > 0:
                stop_too_much_bounce = MIN
            velocity -= total_force
            value += velocity * dt

            # 戻り過ぎへの対策
            if stop_too_much_bounce is MIN and value > min:
                velocity = 0
                value = min
                return False
            if stop_too_much_bounce is MAX and value < max:
                velocity = 0
                value = max
                return False

            if abs(velocity) <= min_velocity:
                if value < min:
                    overscroll = value - min
                elif value > max:
                    overscroll = value - max
                else:
                    overscroll = 0
                if abs(overscroll) <= min_overscroll:
                    velocity = 0
                    if overscroll > 0:
                        value = max
                    elif overscroll < 0:
                        value = min
                    return False
        finally:
            self.value = value
            self.velocity = velocity

    _update = partial(_update, abs, "MAX", "MIN")

    def scroll_by(self, distance):
        ''' 示された量だけ進むように速度を変える。 '''
        self.velocity = distance * self.friction / self.std_dt

    def scroll_to(self, new_value):
        ''' 示された値に行き着くように速度を変える。 '''
        self.scroll_by(new_value - self.value)
