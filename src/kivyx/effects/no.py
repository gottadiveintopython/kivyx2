__all__ = ('KXNoEffect', )
from kivy.event import EventDispatcher
from kivy.properties import NumericProperty


class KXNoEffect(EventDispatcher):
    value = NumericProperty()
    min = NumericProperty()
    max = NumericProperty()
    velocity = NumericProperty()

    def activate(self):
        pass

    def deactivate(self):
        pass

    def scroll_by(self, distance):
        ''' 示された量だけ進むように速度を変える。 '''

    def scroll_to(self, new_value):
        ''' 示された値に行き着くように速度を変える。 '''
