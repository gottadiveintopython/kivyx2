======
Notes
======

.. _two-types-of-behavior-apis:

--------------------------
Two types of behavior APIs
--------------------------

Many features in ``kivyx.uix.behaviors``  provide two types of APIs.

One is a mixin class that allows you to enable, disable and configure its functionality
dynamically through Kivy properties. Kivy users are probably already familiar with this type of API.

.. code-block::

    import asynckivy as ak
    from kivyx.uix.behaviors.tap import KXTapGestureRecognizer

    class MyButton(KXTapGestureRecognizer, Label):
        ...

    btn = MyButton()
    btn.tap_disabled = True  # Disable
    btn.tap_disabled = False  # Enable

    __, touch = await ak.event(btn, "on_tap")

The other is an async function that enables its functionality for a specific
instance rather than for an entire class.

.. code-block::

    import asynckivy as ak
    from kivyx.uix.behaviors.tap import enable_tap_gesture_recognition

    task = ak.start(enable_tap_gesture_recognition(widget), on_tap=...)  # Enable
    task.cancel()  # Disable

This can be particularly useful when you need the functionality only for a short period of time: 

.. code-block::

    from contextlib import closing
    import asynckivy as ak
    from kivyx.uix.behaviors.tap import enable_tap_gesture_recognition

    tap_event = ak.Event()
    with closing(ak.start(enable_tap_gesture_recognition(widget), on_tap=tap_event.fire)):
        __, touch = await tap_event.wait()

The code above waits for a tap gesture on ``widget``.
Once a tap is detected, the ``with`` block exits, automatically disabling the tap gesture recognition.

With this approach, you only incur the cost of gesture recognition while it is actually in use.
In contrast, with the mixin-based approach, the MRO cost is incurred regardless of whether gesture recognition is enabled.
