import pytest
import logging

logger = logging.getLogger(__name__)


class TestClass:

    def setup_class(self):
        logger.info("setup_class called once for the class")

    def teardown_class(self):
        logger.info("teardown_class called once for the class")

    def setup_method(self):
        logger.info("setup_method called for every method")

    def teardown_method(self):
        logger.info("teardown_method called for every method")

    @pytest.mark.ha
    @pytest.mark.tags("TEST-27413")
    def test_one(self):
        self.me = 'self'
        logger.info("    one")
        assert True
        logger.info("    one after")

    @pytest.mark.ha
    @pytest.mark.tags("TEST-27414")
    def test_two(self):
        logger.info("    two")
        assert False
        logger.info("    two after")

    @pytest.mark.ha
    @pytest.mark.tags("TEST-27415")
    def test_three(self):
        logger.info("    three")
        assert True
        logger.info("    three after")
