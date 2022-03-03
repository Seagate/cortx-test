#
# Copyright (c) 2022 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.
#
"""Test and evaluate pytest features."""
import pytest
import logging
from commons import Globals
# import _pytest.logging.LogCaptureFixture
from testfixtures import LogCapture


def setup_module(module):
    logging.getLogger(__name__).info('Entered teardown module')


def teardown_module(module):
    logging.getLogger(__name__).info('Exited teardown module')


def setup_function(function):
    """ setup any state tied to the execution of the given function.
    Invoked for every test function in the module.
    """


def teardown_function(function):
    """ teardown any state that was previously setup with a setup_function
    call.
    """
    # with open(function.__name__, 'w') as f:
    #     for rec in capture.records:
    #         f.write(formatter.format(rec) + '\n')


def max(values):
    _max = values[0]

    for val in values:
        if val > _max:
            _max = val
    logging.getLogger(__name__).info("inner function max is %s" % _max)
    return _max


def min(values):
    _min = values[0]

    for val in values:
        if val < _min:
            _min = val
    logging.getLogger(__name__).info("inner function min is %s" % _min)
    return _min


@pytest.mark.usefixtures("log_cutter")
def test_min(request, capture, logger):
    values = (2, 3, 1, 4, 6)
    val = min(values)
    logger.debug("min is %s" % val)
    logger.warning("min is %s" % val)
    logger.info("min is %s" % val)
    logger.error("min is %s" % val)
    assert val == 1
    records = capture.records
    test_name = request.node.name
    Globals.records.update({test_name: records})


def test_max(capture, logger, formatter):
    values = (2, 3, 1, 4, 6)

    val = max(values)
    logger.info("max is %s" % val)

    assert val == 6
    with open(test_max.__name__, 'w') as f:
        for rec in capture.records:
            f.write(formatter.format(rec) + '\n')


def test_a1(logger):
    logger.info("info")

    assert (1) == (1)


def test_a2(logger):
    logger.info("info")

    assert (1, 2) == (1, 2)


def test_a3(logger):
    logger.info("info")
    assert (1, 2, 3) == (1, 2, 3)


def test_b1(logger):
    logger.info("info")
    assert "falcon" == "fal" + "con"


def test_b2(logger):
    logger.info("info")
    assert "falcon" == f"fal{'con'}"


# pytest -m b test_pytest_features.py

@pytest.mark.parametrize("data, expected", [((2, 3, 1, 4, 6), 1),
                                            ((5, -2, 0, 9, 12), -2), ((200, 100, 0, 300, 400), 0)])
def test_min1(data, expected, logger):
    logger.info("info")
    val = min(data)
    assert val == expected


@pytest.mark.parametrize("data, expected", [((2, 3, 1, 4, 6), 6),
                                            ((5, -2, 0, 9, 12), 12), ((200, 100, 0, 300, 400), 400)])
def test_max1(data, expected, logger):
    logger.info("info")
    val = max(data)
    assert val == expected


@pytest.fixture
def data():
    return [3, 2, 1, 5, -3, 2, 0, -2, 11, 9]


def test_sel_sort(data, logger):
    sorted_vals = data.sort()
    print(sorted_vals)
    logger.info("info %s" % sorted_vals)


@pytest.mark.tags("1501")
def test_function():
    assert True


order = []


@pytest.fixture(scope="session")
def s1():
    order.append("s1")


@pytest.fixture(scope="module")
def m1():
    order.append("m1")


@pytest.fixture
def f1(f3):
    order.append("f1")


@pytest.fixture
def f3():
    order.append("f3")


@pytest.fixture(autouse=True)
def a1():
    order.append("a1")


@pytest.fixture
def f2():
    order.append("f2")


def test_order(f1, m1, f2, s1):
    assert order == ["s1", "m1", "a1", "f3", "f1", "f2"]
