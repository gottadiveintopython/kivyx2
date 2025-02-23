# Kivyx2

Kivyx2 is an experiment to see if widgets can be designed according to the following principles:

- Avoid using `touch.grab()`.  
  - Instead, receive touch events directly from `kivy.core.window.Window`.  
- Avoid simulating touch events.  
  - Widgets like `KXScrollView` immediately dispatch touch events to their children, minimizing input latency.

## A major drawback

The library follows its own touch-handling conventions.
Kivy’s official widgets that respond to touches **may not work properly**.
