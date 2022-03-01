# -*- coding: utf-8 -*-
# !/usr/bin/python
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

"""
Report RPC module handle initiating a report client and update Jira and MongoDB.
These are async rpc calls and intended to be called from pytest reporting hooks.
"""


class ReportClientImpl:
    """Reports test status to Jira and MongoDB"""

    def __init__(self):
        """Init Jira and MongoDB Clients."""

    def async_update_db(self):
        """Async update db with test result."""


def register(srv):
    """
    Registers RPC API.
    :param srv:
    """
    srv.register_instance(ReportClientImpl())
