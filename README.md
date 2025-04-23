# Kivyx2

Kivyx2 is an experiment to explore whether Kivy widgets can be designed according to the following rules:

- Do not use `touch.grab()`.
  - To avoid missing the `on_touch_up` event, use `touch.ud["kivyx_end_signal"]`.
- Do not simulate touch events.  
  - Widgets like `KXScrollView` immediately dispatch touch events to their children, minimizing input latency.

## A major drawback

This library defines its own touch-handling conventions,
so widgets that respond to touches in the standard Kivy way **might not behave as expected**.

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

