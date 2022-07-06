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
#
"""
Stage duration
"""
import argparse
import csv
import os
from commons.utils import web_utils

stages = ['SANITY_TEST_EXECUTION', 'REGRESSION_TEST_EXECUTION', 'IO_PATH_TEST_EXECUTION',
          'FAILURE_DOMAIN_TEST_EXECUTION']
STAGE_DURATION_CSV = 'stages_duration.csv'

def convert_duration(duration_millis):
    """
    converts millisecond to hh:mm:ss
    :param duration_millis: duration in millisecond
    """
    minutes, second = divmod(duration_millis / 1000, 60)
    hour, minute = divmod(minutes, 60)
    duration = f'{hour:0>2.0f}:{minute:0>2.0f}:{second:0>2.0f}'
    return duration


def main():
    """ main function """
    parser = argparse.ArgumentParser(description="Stage Duration")
    parser.add_argument("-bl", help="build url", required=True)
    args = parser.parse_args()
    build_url = args.bl
    resp = web_utils.http_get_request(f"{build_url}wfapi/describe")
    resp_stages = []
    resp_stages.extend(resp.json()["stages"])
    with open(os.path.join(os.getcwd(), STAGE_DURATION_CSV), 'w', newline='', encoding="utf8")\
            as stage_csv:
        writer = csv.writer(stage_csv)
        total_duration = 0
        for stage in resp_stages:
            key = stage['name']
            if key in stages:
                val = stage['durationMillis']
                total_duration += val
                duration = convert_duration(val)
                writer.writerow([key, duration])
        total_duration = convert_duration(total_duration)
        writer.writerow(['Total', total_duration])

if __name__ == "__main__":
    main()
