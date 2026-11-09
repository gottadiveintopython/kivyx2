import pytest

from kivy.tests.common import UnitTestTouch
import asynckivy as ak


names_of_regular_detectors = (
    "horizontal_swipe",
    "long_press",
    "vertical_swipe",
)
names_of_all_detectors = names_of_regular_detectors + ("immediate", )


def get_detector(name):
    import kivyx.gesture_detectors as mod
    return getattr(mod, name)


@pytest.mark.parametrize("name", names_of_regular_detectors)
def test_rightward_swipe(kivy_runner, name):
    kivy_runner.advance_a_frame()
    t = UnitTestTouch(0, 0)
    t.touch_down()
    task = ak.start(get_detector(name)(kivy_runner.window, t))
    t.touch_move(1, 0)
    assert not task.cancelled
    assert not task.finished
    t.touch_move(1000, 0)
    assert not task.cancelled
    assert task.finished is (name == "horizontal_swipe")
    task.cancel()


@pytest.mark.parametrize("name", names_of_regular_detectors)
def test_leftward_swipe(kivy_runner, name):
    kivy_runner.advance_a_frame()
    t = UnitTestTouch(0, 0)
    t.touch_down()
    task = ak.start(get_detector(name)(kivy_runner.window, t))
    t.touch_move(-1, 0)
    assert not task.cancelled
    assert not task.finished
    t.touch_move(-1000, 0)
    assert not task.cancelled
    assert task.finished is (name == "horizontal_swipe")
    task.cancel()


@pytest.mark.parametrize("name", names_of_regular_detectors)
def test_upward_swipe(kivy_runner, name):
    kivy_runner.advance_a_frame()
    t = UnitTestTouch(0, 0)
    t.touch_down()
    task = ak.start(get_detector(name)(kivy_runner.window, t))
    t.touch_move(0, 1)
    assert not task.cancelled
    assert not task.finished
    t.touch_move(0, 1000)
    assert not task.cancelled
    assert task.finished is (name  == "vertical_swipe")
    task.cancel()


@pytest.mark.parametrize("name", names_of_regular_detectors)
def test_downward_swipe(kivy_runner, name):
    kivy_runner.advance_a_frame()
    t = UnitTestTouch(0, 0)
    t.touch_down()
    task = ak.start(get_detector(name)(kivy_runner.window, t))
    t.touch_move(0, -1)
    assert not task.cancelled
    assert not task.finished
    t.touch_move(0, -1000)
    assert not task.cancelled
    assert task.finished is (name  == "vertical_swipe")
    task.cancel()


@pytest.mark.parametrize("name", names_of_regular_detectors)
def test_upward_then_rightward_swipe(kivy_runner, name):
    kivy_runner.advance_a_frame()
    t = UnitTestTouch(0, 0)
    t.touch_down()
    task = ak.start(get_detector(name)(kivy_runner.window, t))
    t.touch_move(0, 1000)
    assert not task.cancelled
    assert task.finished is (name in ("vertical_swipe", ))
    t.touch_move(1000, 1000)
    assert not task.cancelled
    assert task.finished is (name in ("vertical_swipe", "horizontal_swipe", ))
    task.cancel()


@pytest.mark.parametrize("name", names_of_regular_detectors)
def test_long_press(kivy_runner, name):
    kivy_runner.advance_a_frame()
    t = UnitTestTouch(0, 0)
    t.touch_down()
    task = ak.start(get_detector(name)(kivy_runner.window, t))
    kivy_runner.advance_a_frame(dt=0.01)
    assert not task.cancelled
    assert not task.finished
    kivy_runner.advance_a_frame(dt=1.00)
    assert not task.cancelled
    assert task.finished is (name == "long_press")
    task.cancel()


def test_race(kivy_runner):
    from asynckivy import TaskState as TS
    from kivyx.gesture_detectors import long_press, horizontal_swipe
    kr = kivy_runner
    kr.advance_a_frame()
    t = UnitTestTouch(0, 0)
    t.touch_down()
    task = ak.start(ak.wait_any(
        long_press(kr.window, t, min_duration=1.0),
        horizontal_swipe(kr.window,t, min_distance=20),
    ))
    kr.advance_a_frame(dt=0.1)
    assert task.state is TS.STARTED
    t.touch_move(10, 0)
    assert task.state is TS.STARTED
    kr.advance_a_frame(dt=0.1)
    assert task.state is TS.STARTED
    t.touch_move(30, 0)
    assert task.finished
    child_tasks = task.result
    assert child_tasks[0].cancelled
    assert child_tasks[1].finished


@pytest.mark.parametrize("name", names_of_all_detectors)
def test_task_that_starts_monitoring_later_is_notified_earlier(kivy_runner, name):
    kr = kivy_runner
    kr.advance_frame()

    t = UnitTestTouch(0, 0)
    t.touch_down()
    root_task = ak.start(ak.wait_any(
        t.ud["kivyx_gestures"][name].wait(),
        t.ud["kivyx_gestures"][name].wait(),
    ))
    kr.advance_frame(dt=0)
    kr.advance_frame(dt=999)
    t.touch_move(9999, 9999)
    assert root_task.finished
    child_tasks = root_task.result
    assert child_tasks[0].cancelled
    assert child_tasks[1].finished
    t.touch_up()
