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
        ''' Adjust the :attr:`velocity` to achieve a specified movement distance. '''

    def scroll_to(self, new_value):
        '''Adjust the :attr:`velocity` to reach a specified value.'''
