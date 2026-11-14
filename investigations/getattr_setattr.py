'''
scrollview.py の _apply_kinetic_effect の効率の良い実装の検証
'''
from functools import partial
from timeit import timeit

class KXScrollView:
    def __init__(self):
        self.content_x = 0.
        self.content_min_x = 0.
        self.content_max_x = 0.
        self._velocity_x = 0.
        self.content_y = 0.
        self.content_min_y = 0.
        self.content_max_y = 0.
        self._velocity_y = 0.


def _apply_kinetic_effect_ver_A(getattr, setattr, value_attr, min_attr, max_attr, velocity_attr, sv: KXScrollView):
    value = getattr(sv, value_attr)
    min_value = getattr(sv, min_attr)
    max_value = getattr(sv, max_attr)
    velocity = getattr(sv, velocity_attr)
    setattr(sv, value_attr, value)
    setattr(sv, velocity_attr, velocity)
_apply_kinetic_effect_ver_A = partial(_apply_kinetic_effect_ver_A, getattr, setattr)
_apply_kinetic_effect_x_ver_A = partial(_apply_kinetic_effect_ver_A, "content_x", "content_min_x", "content_max_x", "_velocity_x")
_apply_kinetic_effect_y_ver_A = partial(_apply_kinetic_effect_ver_A, "content_y", "content_min_y", "content_max_y", "_velocity_y")


def _apply_kinetic_effect_ver_B(is_horizontal, sv: KXScrollView):
    if is_horizontal:
        value = sv.content_x
        min_value = sv.content_min_x
        max_value = sv.content_max_x
        velocity = sv._velocity_x
    else:
        value = sv.content_y
        min_value = sv.content_min_y
        max_value = sv.content_max_y
        velocity = sv._velocity_y
    if is_horizontal:
        sv.content_x = value
        sv._velocity_x = velocity
    else:
        sv.content_y = value
        sv._velocity_y = velocity
_apply_kinetic_effect_x_ver_B = partial(_apply_kinetic_effect_ver_B, True)
_apply_kinetic_effect_y_ver_B = partial(_apply_kinetic_effect_ver_B, False)


print("effect_x ver.A:", timeit(partial(_apply_kinetic_effect_x_ver_A, KXScrollView())))
print("effect_y ver.A:", timeit(partial(_apply_kinetic_effect_y_ver_A, KXScrollView())))
print("effect_x ver.B:", timeit(partial(_apply_kinetic_effect_x_ver_B, KXScrollView())))
print("effect_y ver.B:", timeit(partial(_apply_kinetic_effect_y_ver_B, KXScrollView())))
