# Kivyx2

Kivyx2 is an experiment to explore whether Kivy widgets can be designed based on the following principles.

- Avoid using `touch.grab()`.  
  - Instead, receive touch events directly from `kivy.core.window.Window`.  
- Avoid simulating touch events.  
  - Widgets like `KXScrollView` immediately dispatch touch events to their children, minimizing input latency.

## A major drawback

The library follows its own touch-handling conventions.
Widgets that respond to touches, including Kivy’s official widgets and other third-party widgets, **may not work properly**.
