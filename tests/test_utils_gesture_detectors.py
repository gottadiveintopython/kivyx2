import pytest

from kivy.tests.common import UnitTestTouch
import asynckivy as ak


names_of_all_detectors = (
    "direction_free_swipe",
    "downward_swipe",
    "horizontal_swipe",
    "leftward_swipe",
    "long_press",
    "rightward_swipe",
    "upward_swipe",
    "vertical_swipe",
)


def get_detector(name):
    import kivyx.gesture_detectors as mod
    return getattr(mod, name)


def test_all_detectors_are_listed():
    from kivyx.gesture_detectors import __all__
    assert set(__all__) == (set(names_of_all_detectors) | {"GestureDetector", "immediate"})


@pytest.mark.parametrize("name", names_of_all_detectors)
def test_move_right(kivy_runner, name):
    kivy_runner.advance_a_frame()
    t = UnitTestTouch(0, 0)
    t.touch_down()
    task = ak.start(get_detector(name)(t))
    t.touch_move(1, 0)
    assert not task.cancelled
    assert not task.finished
    t.touch_move(1000, 0)
    assert not task.cancelled
    assert task.finished is (name in ("rightward_swipe", "horizontal_swipe", "direction_free_swipe"))
    task.cancel()


@pytest.mark.parametrize("name", names_of_all_detectors)
def test_move_left(kivy_runner, name):
    kivy_runner.advance_a_frame()
    t = UnitTestTouch(0, 0)
    t.touch_down()
    task = ak.start(get_detector(name)(t))
    t.touch_move(-1, 0)
    assert not task.cancelled
    assert not task.finished
    t.touch_move(-1000, 0)
    assert not task.cancelled
    assert task.finished is (name in ("leftward_swipe", "horizontal_swipe", "direction_free_swipe"))
    task.cancel()


@pytest.mark.parametrize("name", names_of_all_detectors)
def test_move_up(kivy_runner, name):
    kivy_runner.advance_a_frame()
    t = UnitTestTouch(0, 0)
    t.touch_down()
    task = ak.start(get_detector(name)(t))
    t.touch_move(0, 1)
    assert not task.cancelled
    assert not task.finished
    t.touch_move(0, 1000)
    assert not task.cancelled
    assert task.finished is (name in ("upward_swipe", "vertical_swipe", "direction_free_swipe"))
    task.cancel()


@pytest.mark.parametrize("name", names_of_all_detectors)
def test_move_down(kivy_runner, name):
    kivy_runner.advance_a_frame()
    t = UnitTestTouch(0, 0)
    t.touch_down()
    task = ak.start(get_detector(name)(t))
    t.touch_move(0, -1)
    assert not task.cancelled
    assert not task.finished
    t.touch_move(0, -1000)
    assert not task.cancelled
    assert task.finished is (name in ("downward_swipe", "vertical_swipe", "direction_free_swipe"))
    task.cancel()


@pytest.mark.parametrize("name", names_of_all_detectors)
def test_move_up_then_move_right(kivy_runner, name):
    kivy_runner.advance_a_frame()
    t = UnitTestTouch(0, 0)
    t.touch_down()
    task = ak.start(get_detector(name)(t))
    t.touch_move(0, 1000)
    assert not task.cancelled
    assert task.finished is (name in ("upward_swipe", "vertical_swipe", "direction_free_swipe"))
    t.touch_move(1000, 1000)
    assert not task.cancelled
    assert task.finished is (name in ("upward_swipe", "vertical_swipe", "rightward_swipe", "horizontal_swipe", "direction_free_swipe"))
    task.cancel()


@pytest.mark.parametrize("name", names_of_all_detectors)
def test_stay(kivy_runner, name):
    kivy_runner.advance_a_frame()
    t = UnitTestTouch(0, 0)
    t.touch_down()
    task = ak.start(get_detector(name)(t))
    kivy_runner.advance_a_frame(dt=0.01)
    assert not task.cancelled
    assert not task.finished
    kivy_runner.advance_a_frame(dt=1.00)
    assert not task.cancelled
    assert task.finished is (name in ("long_press", ))
    task.cancel()


def test_race(kivy_runner):
    from asynckivy import TaskState as TS
    from kivyx.gesture_detectors import long_press, rightward_swipe
    kivy_runner.advance_a_frame()
    t = UnitTestTouch(0, 0)
    t.touch_down()
    task = ak.start(ak.wait_any(
        long_press(t, min_duration=1.0),
        rightward_swipe(t, min_movement=20),
    ))
    kivy_runner.advance_a_frame(dt=0.1)
    assert task.state is TS.STARTED
    t.touch_move(10, 0)
    assert task.state is TS.STARTED
    kivy_runner.advance_a_frame(dt=0.1)
    assert task.state is TS.STARTED
    t.touch_move(30, 0)
    assert task.finished
    child_tasks = task.result
    assert child_tasks[0].cancelled
    assert child_tasks[1].finished
