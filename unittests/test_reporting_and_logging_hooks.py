"""Sample module to be referred while writing tests."""
import os
import logging
import pytest


# Do not set logging after imports
# log = logging.getLogger(__name__)
# cortxlogging.init_loghandler(log)

def setup_module(module):
    """Setup module."""
    print('Entered teardown module')


def teardown_module(module):
    """Tear module."""
    print('Exited teardown module')


def setup_function(function):
    """
    Setup any state tied to the execution of the given function.
    Invoked for every test function in the module.
    """
    print('Entered setup function')


def teardown_function(function):
    """Teardown any state that was previously setup with a setup_function call."""
    print('Exited teardown function')


def max(values):
    """A test function."""
    _max = values[0]

    for val in values:
        if val > _max:
            _max = val
    logging.getLogger(__name__).info("inner function max is %s" % _max)
    return _max


def min(values):
    """A test function."""
    _min = values[0]

    for val in values:
        if val < _min:
            _min = val
    logging.getLogger(__name__).info("inner function min is %s" % _min)
    return _min


@pytest.mark.tags("TEST-17495")
def test_min_lc(logger):
    """
    Alternate way to cut logs for each test.
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


@pytest.mark.tags("TEST-17496")
def test_max_lc(logger):
    """A test function."""
    values = (2, 3, 1, 4, 6)
    val = max(values)
    logger.info("max is %s" % val)
    assert val == 6

@pytest.mark.s3_ops
@pytest.mark.parallel
@pytest.mark.tags("TEST-17413")
def test_min(logger):
    """
    Preferred way to cut logs for each test and sample to be referred to
    write test cases.
    :param logger:
    :return:
    """
    logger.info("PYTEST_XDIST_WORKER value is" + str(os.environ.get('PYTEST_XDIST_WORKER')))
    values = (2, 3, 1, 4, 6)
    val = min(values)
    logger.debug("min is %s" % val)
    logger.warning("min is %s" % val)
    logger.info("min is %s" % val)
    logger.error("min is %s" % val)
    assert val == 1


@pytest.mark.s3_ops
@pytest.mark.parallel
@pytest.mark.tags("TEST-17414")
def test_max(logger):
    """A test function."""
    values = (2, 3, 1, 4, 6)
    val = max(values)
    logger.info("max is %s" % val)
    assert val == 6

@pytest.mark.s3_ops
@pytest.mark.parallel
@pytest.mark.tags("TEST-17498")
def test_max2(logger):
    """A test function."""
    values = (2, 3, 1, 4, 6)
    val = max(values)
    logger.info("max is %s" % val)
    assert val == 6
    logger.info("xdist" + str(os.environ.get('PYTEST_XDIST_WORKER')))


@pytest.mark.s3_ops
@pytest.mark.parallel
@pytest.mark.tags("TEST-17497")
def test_max4(logger):
    """A test function."""
    logger.info("test pass executed")


@pytest.mark.s3_ops
@pytest.mark.parallel
@pytest.mark.tags("TEST-17499")
def test_max3(logger):
    """A test function."""
    values = (2, 3, 1, 4, 6)
    val = max(values)
    logger.info("max is %s" % val)
    assert val == 6
