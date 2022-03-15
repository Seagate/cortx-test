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
import logging
import pytest

logger = logging.getLogger(__name__)


class TestClass:

    def setup_class(self):
        """N unit style Class level setup interceptor or fixture."""
        logger.info("setup_class called once for the class")

    def teardown_class(self):
        """N unit Style Class level teardown interceptor."""
        logger.info("teardown_class called once for the class")

    def setup_method(self):
        """Method level setup interceptor."""
        logger.info("setup_method called for every method")

    def teardown_method(self):
        """Method level teardown interceptor."""
        logger.info("teardown_method called for every method")

    @pytest.mark.ha
    @pytest.mark.tags("TEST-27413")
    def test_one(self):
        """Sample UnitTest"""
        self.me = 'self'
        logger.info("    one")
        assert True
        logger.info("    one after")

    @pytest.mark.ha
    @pytest.mark.tags("TEST-27414")
    def test_two(self):
        """Failing UnitTest"""
        logger.info("    two")
        assert False
        logger.info("    two after")

    @pytest.mark.ha
    @pytest.mark.tags("TEST-27415")
    def test_three(self):
        """Another passed UnitTest"""
        logger.info("    three")
        assert True
        logger.info("    three after")
