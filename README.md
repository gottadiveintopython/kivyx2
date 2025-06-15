# Kivyx2

Kivyx2 is an experiment to explore whether Kivy widgets can be designed according to the following rules:

- Do not use `touch.grab()`.
  - To avoid missing `on_touch_up` events, listen to `touch.ud["kivyx_end_signal"]`.
  - To avoid missing `on_touch_move` events, directly receive them from the `kivy.core.window.Window`.
- Do not simulate touch events.  
  - Widgets like `KXScrollView` immediately dispatch touch events to their children, minimizing input latency.
- A widget that wants to claim exclusive access to a touch must call `touch.ud["kivyx_claim_signal"].fire()` to notify other widgets.
- A widget that is interested in a touch and may later claim exclusive access must listen to `touch.ud["kivyx_claim_signal"]`.
  If another widget claims the touch first, it must relinquish its claim to exclusive access.

For instance, when a user places a finger on a `KXScrollView` widget,
it begins not only tracking the finger's movement but also listening to `touch.ud["kivyx_claim_signal"]`.
At this point, the `KXScrollView` cannot immediately claim exclusive access to the touch, as it may not yet be a scrolling gesture.
Then, if the finger travels a certain distance before any other widget calls `touch.ud["kivyx_claim_signal"].fire()`,
the `KXScrollView` will recognize the touch as a scrolling gesture and will call the `fire` method to gain exclusive access.


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

