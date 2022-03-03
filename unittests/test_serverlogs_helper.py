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
"""Test server log library."""
import pytest
from commons.helpers import serverlogs_helper
from datetime import datetime

now = datetime.now()
current_time = now.strftime('%b  %#d %H:%M:%S')


def test_serverlogs_lib():
    # Before running following unit test, make sure the corrsponding file is placed
    # on the nodes/server
    start_time = "Dec 12 16:06:01"
    end_time = "Dec 12 16:12:07"
    serverlogs_helper.collect_logs_fromserver(st_time=start_time,
                                              end_time=end_time,
                                              file_type="motr",
                                              node="node1",
                                              test_suffix="0707")
    
