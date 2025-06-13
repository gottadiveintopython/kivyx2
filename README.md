# Kivyx2

Kivyx2 is an experiment to explore whether Kivy widgets can be designed according to the following rules:

- Do not use `touch.grab()`.
  - To avoid missing `on_touch_up` events, wait for `touch.ud["kivyx_end_signal"]` to fire.
  - To avoid missing `on_touch_move` events, directly receive them from the `kivy.core.window.Window`.
- Do not simulate touch events.  
  - Widgets like `KXScrollView` immediately dispatch touch events to their children, minimizing input latency.
- A widget that decides to handle a touch must fire `touch.ud["kivyx_claim_signal"]` to notify other widgets.
  - Consequently, if a widget is interested in a touch but not yet ready to handle it, it should listen for `touch.ud["kivyx_claim_signal"]` and relinquish its interest if another widget claims the touch.

## A major drawback

Due to the rules above, widgets that respond to touches in the standard Kivy way **might not behave as expected**.

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

