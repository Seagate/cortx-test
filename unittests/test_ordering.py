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
"""Test pytest oderdering."""
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