# Kivyx2

Kivyx2 is an experiment to explore whether Kivy widgets can be designed according to the following rules:

- Do not use `touch.grab()`.
  - To avoid missing `on_touch_up` events, listen for `touch.ud["kivyx_end_event"]`.
  - To avoid missing `on_touch_move` events, directly receive them from the `kivy.core.window.Window`.
- Do not simulate touch events.  
  - Widgets like `KXScrollView` immediately dispatch touch events to their children, minimizing input latency.
- A widget that wants exclusive access to a touch must call its `touch.ud["kivyx_exclusive_access"].claim()` method to notify other widgets.
  - If exclusive access to the touch has been already claimed (i.e. `touch.ud["kivyx_exclusive_access"].has_been_claimed` is True),
    the widget must relinquish it.
- A widget that is interested in a touch and may later claim exclusive access may want to listen for the `touch.ud["kivyx_exclusive_access"]` event.
  This allows the widget to perform other tasks while still being able to respond to a claim from another widget.

```python
import asynckivy as ak

async def touch_handler(self, touch):
    e_access = touch.ud["kivyx_exclusive_access"]
    async with ak.move_on_when(e_access.wait_for_someone_to_claim()):
        # Do something while listening for exclusive access claims from others
        ...
    if e_access.has_been_claimed:
        return
    # No one has claimed exclusive access yet so you can safely claim it
    e_access.claim()
```

For instance, when a user places a finger on a `KXScrollView` widget,
it begins not only tracking the finger's movement but also listening for the `touch.ud["kivyx_exclusive_access"]` event.
At this point, the `KXScrollView` cannot immediately claim exclusive access to the touch, as it may not yet be a scrolling gesture.
Then, if the finger travels a certain distance before any other widget claims exclusive access,
the `KXScrollView` will recognize the touch as a scrolling gesture, claim exclusive access, and begin scrolling.

## A major drawback

Due to the rules above, widgets that handle touches in the standard Kivy way **might not behave as expected**.

## Issues

- Due to issues with Sphinx, the documentation isn't up to date with the codebase.

## Components

### Behaviors

| Kivyx component | Equivalent to |
|:---|:---|
| KXTapGestureRecognizer | ButtonBehavior |
| KXMultiTapGestureRecognizer |
| KXTouchRippleBehavior | TouchRippleBehavior |
| KXDraggableBehavior <br> KXDragReorderBehavior <br> KXDragTargetBehavior | kivy-garden-draggable |

### Widgets

| Kivyx component | Equivalent to |
|:---|:---|
| KXButton | Button |
| KXMultiTapButton | |
| KXScrollView | ScrollView |
| KXSwitch | Switch |

