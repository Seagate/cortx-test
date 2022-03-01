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

@pytest.fixture(autouse=True)
def capture():
    with LogCapture() as logs:
        yield logs


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
