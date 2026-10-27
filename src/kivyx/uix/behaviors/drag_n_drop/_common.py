from typing import TypeAlias
from collections.abc import Collection, Set

DropTags: TypeAlias = Set
DragTags: TypeAlias = Collection
DEFAULT_DROP_TAGS: DropTags = frozenset((None, ))
DEFAULT_DRAG_TAGS: DragTags = DEFAULT_DROP_TAGS
