""" Test Plan clone utility."""
#
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.
#
# -*- coding: utf-8 -*-

import os
import sys
import argparse
import csv
from datetime import datetime
import jira_api

# cloned test plan csv name
CLONED_TP_CSV = 'cloned_tp_info.csv'

def main(args):
    """
    main function to clone test plan
    """
    jira_id, jira_pwd = jira_api.get_username_password()
    test_plan = args.test_plan

    tp_info = dict()
    tp_info['build'] = args.build
    tp_info['build_type'] = args.build_type
    tp_info['setup_type'] = args.setup_type

    new_tp_key = jira_api.create_new_test_plan(test_plan, jira_id, jira_pwd, tp_info)
    if new_tp_key == '':
        sys.exit('New test plan creation failed')
    else:
        print("New test plan {} created".format(new_tp_key))

    test_executions = jira_api.get_test_executions_from_test_plan(test_plan, jira_id, jira_pwd)
    te_keys = [te["key"] for te in test_executions]
    print("test executions of existing test plan {}".format(te_keys))

    new_te_keys = []
    for te in te_keys:
        # create new te
        new_te_id = jira_api.create_new_test_exe(te, jira_id, jira_pwd, tp_info)
        new_te_keys.append(new_te_id)
        response = jira_api.add_tests_to_te_tp(te, new_te_id, new_tp_key, jira_id, jira_pwd)
        if response:
            print("Tests added to TE {} and TP {}".format(new_te_id,new_tp_key))
        else:
            print("Error while adding tests to TE {} and TP {}".format(new_te_id,new_tp_key))

    response = jira_api.add_te_to_tp(new_te_keys, new_tp_key, jira_id, jira_pwd)
    if response:
        print("TEs are added to TP")
    else:
        print("Error while adding TEs to TP")

    print("New Test Plan: {}".format(new_tp_key))
    with open(os.path.join(os.getcwd(),  CLONED_TP_CSV), 'w', newline='') as tp_info_csv:
        writer = csv.writer(tp_info_csv)
        for te in new_te_keys:
            writer.writerow([new_tp_key.strip(), te.strip()])

    if args.comment_jira:
        current_time_ms = datetime.utcnow().strftime('%Y-%m-%d_%H:%M:%S.%f')
        comment = ' Build: {}, Setup: {}, Test Plan: {}, Test Executions: {} created on {}'. \
            format(args.build, args.setup_type, new_tp_key, new_te_keys, current_time_ms)
        jira_api.add_comment(args.comment_jira, comment, jira_id, jira_pwd)


def parse_args():
    """
    parse user args
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-tp", "--test_plan", type=str,
                        help="jira xray test plan id", required=True)
    parser.add_argument("-b", "--build", type=str,
                        help="Build number", required=True)
    parser.add_argument("-bt", "--build_type", type=str, default='stable',
                        help="Build type (stable/main)", required=True)
    parser.add_argument("-s", "--setup_type", type=str, default='regular',
                        help="Setup type (regular/nearfull/isolated)", required=True)
    parser.add_argument("-c", "--comment_jira", type=str,
                        help="Test id where comments to be added")
    return parser.parse_args()


if __name__ == '__main__':
    opts = parse_args()
    main(opts)
