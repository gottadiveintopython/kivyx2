from typing import TypeAlias, Any
from collections.abc import Collection

DragCls: TypeAlias = Any
DragClasses: TypeAlias = Collection


def noop(*args, **kwargs): pass


class AcceptAnyType:
    def __contains__(self, item): return True
    def __repr__(self): return "<ACCEPT_ANY>"
    def __str__(self): return "ACCEPT_ANY"


ACCEPT_ANY = AcceptAnyType()
'''
A special value for ``drag_classes`` parameters that indicates that
dragged widgets of any class should be accepted.
'''

AcceptAnyType
