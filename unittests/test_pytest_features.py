import pytest
import smtplib
import logging


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


logging.basicConfig(format='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
init_loghandler(logger)

def max(values):

    _max = values[0]

    for val in values:
        if val > _max:
            _max = val

    return _max


def min(values):

    _min = values[0]

    for val in values:
        if val < _min:
            _min = val
    logger.info("min is %s" % _min)
    return _min

@pytest.mark.skip
def test_min():
    values = (2, 3, 1, 4, 6)
    val = min(values)
    logger.info("min is %s" % val)
    assert val == 2


def test_max():
    values = (2, 3, 1, 4, 6)

    val = max(values)
    logger.info("max is %s" % val)

    assert val == 6


@pytest.mark.a
def test_a1():
    logger.info("info")

    assert (1) == (1)


@pytest.mark.a
def test_a2():
    logger.info("info")

    assert (1, 2) == (1, 2)


@pytest.mark.a
def test_a3():
    logger.info("info")
    assert (1, 2, 3) == (1, 2, 3)


@pytest.mark.b
def test_b1():
    logger.info("info")
    assert "falcon" == "fal" + "con"


@pytest.mark.b
def test_b2():
    logger.info("info")
    assert "falcon" == f"fal{'con'}"

#pytest -m b test_pytest_features.py

@pytest.mark.parametrize("data, expected", [((2, 3, 1, 4, 6), 1),
                                            ((5, -2, 0, 9, 12), -2), ((200, 100, 0, 300, 400), 0)])
def test_min1(data, expected):
    logger.info("info")
    val = min(data)
    assert val == expected

@pytest.mark.parametrize("data, expected", [((2, 3, 1, 4, 6), 6),
                                            ((5, -2, 0, 9, 12), 12), ((200, 100, 0, 300, 400), 400)])
def test_max1(data, expected):
    logger.info("info")
    val = max(data)
    assert val == expected


@pytest.fixture
def data():

    return [3, 2, 1, 5, -3, 2, 0, -2, 11, 9]


def test_sel_sort(data):
    sorted_vals = data.sort()
    print(sorted_vals)
    logger.info("info %s" % sorted_vals)



@pytest.mark.test_id(1501)
def test_function():
    assert True

"""
#scope="session"
@pytest.fixture(scope="module")
def smtp_connection():
    smtp_connection = smtplib.SMTP("smtp.gmail.com", 587, timeout=5)
    yield smtp_connection  # provide the fixture value
    print("teardown smtp")
    smtp_connection.close()


@pytest.fixture(scope="module")
def smtp_connection():
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=5) as smtp_connection:
        yield smtp_connection  # provide the fixture value


def test_ehlo(smtp_connection):
    response, msg = smtp_connection.ehlo()
    assert response == 250
    assert b"smtp.gmail.com" in msg
    assert 0  # for demo purposes


def determine_scope(fixture_name, config):
    if config.getoption("--keep-containers", None):
        return "session"
    return "function"


@pytest.fixture(scope=determine_scope)
def docker_container():
    yield spawn_container()
"""


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


