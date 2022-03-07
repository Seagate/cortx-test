#!/usr/bin/python
# -*- coding: utf-8 -*-
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

"""Function to call robot in python file"""

import os
import logging
from robot import run_cli

LOGGER = logging.getLogger(__name__)


def trigger_robot(arg_dict):
    """
    Trigger robot test
    """
    try:
        log_path = os.path.join(arg_dict['log_path'], 'output.xml')
    except KeyError:
        LOGGER.error("Log path is not provided")
        return False
    cmd_line = form_run_cli_cmd(arg_dict)
    print(cmd_line)
    LOGGER.info("Robot command line is {}".format(cmd_line))
    print('Run robot command line')
    run_cli(cmd_line, exit=False)
    print('Robot cli execution done')
    LOGGER.info("Robot log path is {}".format(log_path))
    with open(log_path, 'r') as f:
        data = f.read()
        if 'fail="1"' in data or 'fail="2"' in data:
            return False
        else:
            return True


def form_run_cli_cmd(arg_dict):
    """
    Form command line for robot test
    """
    cmd = []
    test_path = ''
    for k, v in arg_dict.items():
        if k == 'log_path':
            cmd.append('-d')
            cmd.append(v)
        elif k == 'variable':
            for item in v:
                cmd.append('-v')
                cmd.append(item)
        elif k == 'tag':
            cmd.append('-i')
            cmd.append(v)
        elif k == 'test':
            cmd.append('-t')
            cmd.append(v)
        elif k == 'test_path':
            test_path = v
    cmd.append(test_path)
    return cmd
