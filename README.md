# Kivyx2

Kivyx2 is an experiment to explore whether Kivy widgets can be designed according to the following rules:

- Do not use `touch.grab()`.
  - To avoid missing `on_touch_up` events, listen for `touch.ud["kivyx_end"]`.
  - To avoid missing `on_touch_move` events, directly receive them from the `kivy.core.window.Window`.
- Do not emulate touch events.
  - Widgets like `KXScrollView` immediately dispatch touch events to their children, minimizing input latency.
- A widget that is interested in a touch must listen for its `touch.ud["kivyx_abandon"]` event.
  If the event is fired, the widget must cancel any operations associated with the touch.
- A widget that wants exclusive access to a touch must call its `touch.ud["kivyx_exclusive_access"].claim()` method to notify other widgets.
  - If exclusive access to the touch has already been claimed (i.e. `touch.ud["kivyx_exclusive_access"].has_been_claimed` is True),
    the widget must relinquish it.
- A widget that is interested in a touch and may later claim exclusive access must listen for the `touch.ud["kivyx_exclusive_access"]` event.
  This allows the widget to perform other tasks while still being able to react when another widget claims exclusive access.

```python
import asynckivy as ak

async def touch_handler(self, touch):
    async with ak.move_on_when(touch.ud["kivyx_abandon"].wait()):
        ex_access = touch.ud["kivyx_exclusive_access"]
        async with ak.move_on_when(ex_access.wait_for_one_to_claim()):
            # Monitor touch movements to detect gestures while listening for exclusive access claims
            ...
        if ex_access.has_been_claimed:
            return

        # No one has claimed exclusive access yet so you can safely claim it.
        ex_access.claim(self)

        # Do whatever you want with the touch.
        ...
```

For instance, when a user places a finger on a `KXScrollView` widget,
it begins not only tracking the finger's movement but also listening for the `touch.ud["kivyx_exclusive_access"]` event.
At this point, the `KXScrollView` cannot immediately claim exclusive access to the touch, as the gesture may not yet be identified as a scrolling gesture.
Then, if the finger travels a certain distance before any other widget claims exclusive access,
the `KXScrollView` will recognize the touch as a scrolling gesture, claim exclusive access, and begin scrolling.

## A major drawback

Due to the rules above, widgets that handle touches in the standard Kivy way **might not behave as expected**.

## Notes

- When using Kivy 2.3.1 or earlier, use `kivyx.utils.touchring` instead of `kivy.modules.touchring`.
  ```python
  import asynckivy as ak
  from kivyx.utils.touchring import enable_touch_ring

  ak.managed_start(enable_touch_ring())
  ```
