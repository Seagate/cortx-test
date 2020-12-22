import pytest
import logging
import pytest_ordering

@pytest.mark.run(order=2)
def test_foo():
    assert False

@pytest.mark.run(order=1)
def test_bar():
    assert True

def test_foo(caplog):
    caplog.set_level(logging.INFO)
    pass

def test_foo1(caplog):
    caplog.set_level(logging.CRITICAL, logger="root.baz")
    pass

def test_bar(caplog):
    with caplog.at_level(logging.CRITICAL, logger="root.baz"):
        pass

# content of test_sample.py
def func(x):
    return x + 1


def test_answer():
    assert func(3) == 5