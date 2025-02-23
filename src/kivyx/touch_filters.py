__all__ = (
    "is_opos_colliding_and_not_wheel", "is_opos_colliding", "is_colliding",
    "is_colliding_and_not_wheel",
)


def is_opos_colliding_and_not_wheel(w, t):
    return w.collide_point(*t.opos) and (not t.is_mouse_scrolling)


def is_colliding_and_not_wheel(w, t):
    return w.collide_point(*t.pos) and (not t.is_mouse_scrolling)


def is_opos_colliding(w, t):
    return w.collide_point(*t.opos)


def is_colliding(w, t):
    return w.collide_point(*t.pos)
