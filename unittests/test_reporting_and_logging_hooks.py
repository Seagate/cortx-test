import pytest
import logging
from commons import Globals
# import _pytest.logging.LogCaptureFixture
from testfixtures import LogCapture
from _pytest import runner


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

@pytest.mark.tags("TEST-17495")
@pytest.mark.usefixtures("log_cutter")
def test_min_lc(request, capture, logger):
    """
    Alternate way to cut logs for each test
    :param request:
    :param capture:
    :param logger:
    :return:
    """
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

@pytest.mark.tags("TEST-17496")
@pytest.mark.usefixtures("log_cutter")
def test_max_lc(request, capture, logger):
    values = (2, 3, 1, 4, 6)

    val = max(values)
    logger.info("max is %s" % val)
    assert val == 6
    records = capture.records
    test_name = request.node.name
    Globals.records.update({test_name: records})


@pytest.mark.parallel
@pytest.mark.tags("TEST-17413")
def test_min(logger):
    """
    Preferred way to cut logs for each test and sample to be refered to
    write test cases.
    :param logger:
    :return:
    """
    values = (2, 3, 1, 4, 6)
    val = min(values)
    logger.debug("min is %s" % val)
    logger.warning("min is %s" % val)
    logger.info("min is %s" % val)
    logger.error("min is %s" % val)
    assert val == 1

@pytest.mark.parallel
@pytest.mark.tags("TEST-17414")
def test_max(request, capture, logger):
    values = (2, 3, 1, 4, 6)
    val = max(values)
    logger.info("max is %s" % val)
    assert val == 6
