=============
Touch Filters
=============

The ``kivyx.touch_filters`` module provides a collection of *touch filters* that can be used with
:mod:`asynckivy` to selectively handle touch events. For example:

.. code-block::

    import asynckivy as ak
    from kivyx.touch_filters import is_colliding

    await ak.event(widget, "on_touch_down", filter=is_colliding)

    with ak.suppress_event(widget, "on_touch_down", filter=is_colliding):
        ...

.. automodule:: kivyx.touch_filters

Implementations
================

.. literalinclude:: ../../src/kivyx/touch_filters.py
