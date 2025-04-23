import pytest
from kivy.event import EventDispatcher
from kivy.properties import ListProperty


@pytest.fixture(scope="module")
def holder_cls():
    class ListHolder(EventDispatcher):
        list_obj = ListProperty(None)

    return ListHolder


@pytest.fixture()
def holder(holder_cls):
    return holder_cls()


def test_notification_count(holder):
    history = []
    holder.bind(list_obj=lambda *__: history.append(None))
    holder.list_obj = [1, 2, 3]
    assert len(history) == 1
    obj = holder.list_obj
    obj.append(4)
    assert len(history) == 2
    obj.remove(1)
    assert len(history) == 3
    holder.list_obj = obj
    assert len(history) == 3
