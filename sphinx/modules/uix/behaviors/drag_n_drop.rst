============
Drag & Drop
============

drop_tags & drag_tags
=====================

These two parameters work together as a filter.

For a dragged widget to be accepted by a drop target, their tags must have at least one element in common.
For example:

.. code-block::

    import asynckivy as ak
    import kivyx.uix.behaviors.drag_n_drop as dnd

    ak.managed_start(dnd.enable_drag(widget1, drag_tags={"A", "B"}))
    ak.managed_start(dnd.enable_drop_target(widget2, drop_tags={"B", "C"}))

In this example, ``widget1`` can be dropped onto ``widget2`` because they share the tag ``"B"``.

* A tag doesn't have to be a string; it can be any hashable object.
* "drop_tags" must be a :class:`~collections.abc.Set`, whereas "drag_tags" can be any :class:`~collections.abc.Collection`
  (``drop_tags.isdisjoint(drag_tags)`` must be a valid expression).

API Reference
=============

.. automodule:: kivyx.uix.behaviors.drag_n_drop

