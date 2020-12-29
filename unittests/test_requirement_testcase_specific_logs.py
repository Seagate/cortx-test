import pytest
import logging
from commons import Globals
# import _pytest.logging.LogCaptureFixture
from testfixtures import LogCapture

def init_loghandler(log):
    log.setLevel(logging.DEBUG)
    fh = logging.FileHandler('pytestfeatures.log', mode='a')
    fh.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    log.addHandler(fh)
    log.addHandler(ch)

@pytest.fixture(scope='session')
def formatter():
    format_log_message = '%(asctime)s\t%(levelname)s\t%(filename)s\t%(funcName)s\t%(processName)s\t%(message)s'
    formatter = logging.Formatter(fmt=format_log_message, datefmt='%Y-%m-%d %H:%M:%S')
    return formatter

@pytest.fixture(scope='session')
def logger():
    logging.basicConfig(format='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    init_loghandler(logger)
    return logger


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

@pytest.fixture(scope='function')
def log_cutter(request, formatter):
    print("setup")
    name = request.function.__name__
    records = dict()
    yield records
    records = Globals.records.get(name)
    print("teardown")
    with open(name, 'w') as f:
        for rec in records:
            f.write(formatter.format(rec) + '\n')

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
    # with open(test_min.__name__, 'w') as f:
    #     for rec in capture.records:
    #         f.write(formatter.format(rec) + '\n')
