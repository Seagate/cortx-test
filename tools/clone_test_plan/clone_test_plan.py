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
from jira_api import JiraTask
from multiprocessing import Process, Manager

# cloned test plan csv name
CLONED_TP_CSV = 'cloned_tp_info.csv'

jira_task = JiraTask()

# te's to skip for ova
ova_skip_tes = ['TEST-21365', 'TEST-21133', 'TEST-19721', 'TEST-19720', 'TEST-19719', 'TEST-19717',
                'TEST-19716', 'TEST-19709', 'TEST-19708', 'TEST-19707', 'TEST-19704', 'TEST-19701']

vm_hw_skip_tes = ['TEST-19713']


def process_te(te, tp_info, skip_tes, new_tp_key, new_skipped_te, new_te_keys, old_tes,
               product_family):
    """
    Process existing te and create new te
    """
    # create new te
    jt = JiraTask()
    new_te_id, is_te_skipped, test_list = jt.create_new_test_exe(te, tp_info, skip_tes,
                                                                 product_family)
    if new_te_id != '':
        print("New TE created, now add tests to te and tp")
        response = jt.add_tests_to_te_tp(new_te_id, new_tp_key, tp_info, test_list)
        if response:
            print("Tests added to TE {} and TP {}".format(new_te_id, new_tp_key))
            new_te_keys.append(new_te_id)
            old_tes.append(te)
            if is_te_skipped:
                new_skipped_te.append(new_te_id)
            response_add = jt.add_te_to_tp([new_te_id], new_tp_key)
            if response_add:
                print("TEs are added to TP")
            else:
                print("Error while adding TEs to TP")
        else:
            print("Error while adding tests to TE {} and TP {}".format(new_te_id, new_tp_key))


def main(args):
    """
    main function to clone test plan
    """
    test_plan = args.test_plan

    tp_info = dict()
    tp_info['build'] = args.build
    tp_info['build_branch'] = args.build_branch
    tp_info['setup_type'] = args.setup_type
    tp_info['platform'] = args.platform
    tp_info['nodes'] = args.nodes
    tp_info['server_type'] = args.server_type
    tp_info['enclosure_type'] = args.enclosure_type
    tp_info['affect_version'] = args.affect_version
    tp_info['fix_version'] = args.fix_version
    tp_info['product_family'] = args.product_family
    tp_info['core_category'] = args.core_category
    tp_info['tp_labels'] = args.tp_labels

    new_tp_key, env_field = jira_task.create_new_test_plan(test_plan, tp_info)
    if new_tp_key == '':
        sys.exit('New test plan creation failed')
    else:
        print("New test plan {} created".format(new_tp_key))
        tp_info['env'] = env_field

    test_executions = jira_task.get_test_executions_from_test_plan(test_plan)
    te_keys_all = [te["key"] for te in test_executions]
    platform = args.platform
    if platform.lower() == 'ova':
        te_keys = [te for te in te_keys_all if te not in ova_skip_tes]
        tp_info['platform'] = 'VM'
    else:
        te_keys = [te for te in te_keys_all if te not in vm_hw_skip_tes]

    if args.skip_te_clone:
        te_keys = [te for te in te_keys if te not in args.skip_te_clone]

    if args.tes_to_clone:
        if args.tes_to_clone[0] != "optional":
            new_te_keys = [te for te in te_keys if te in args.tes_to_clone]
            te_keys = new_te_keys

    print("test executions of existing test plan {}".format(te_keys))

    skip_tes = []

    if args.skip_te:
        try:
            skip_te_arg = args.skip_te
            skip_tes = [ele.strip() for ele in skip_te_arg]
        except Exception as e:
            print(f"Exception {e} in getting processing skip tes")

    prcs = []
    with Manager() as manager:
        new_skipped_te = manager.list()
        new_te_keys = manager.list()
        old_tes = manager.list()
        for te in te_keys:
            p = Process(target=process_te, args=(te, tp_info, skip_tes, new_tp_key,
                                                 new_skipped_te, new_te_keys, old_tes,
                                                 args.product_family))
            p.start()
            prcs.append(p)

        for prc in prcs:
            prc.join()

        new_skipped_te = list(new_skipped_te)
        new_te_keys = list(new_te_keys)
        old_tes = list(old_tes)
        print("New Test Plan: {}".format(new_tp_key))
        with open(os.path.join(os.getcwd(), CLONED_TP_CSV), 'w', newline='') as tp_info_csv:
            writer = csv.writer(tp_info_csv)
            for i, te in enumerate(new_te_keys):
                old_te = old_tes[i]
                if te not in new_skipped_te:
                    writer.writerow([new_tp_key.strip(), te.strip(), old_te.strip()])

        if args.comment_jira:
            current_time_ms = datetime.utcnow().strftime('%Y-%m-%d_%H:%M:%S.%f')
            comment = ' Build: {}, Setup: {}, Test Plan: {}, Test Executions: {} created on {}'. \
                format(args.build, args.setup_type, new_tp_key, new_te_keys, current_time_ms)
            jira_task.add_comment(args.comment_jira, comment)


def parse_args():
    """
    parse user args
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-tp", "--test_plan", type=str,
                        help="jira xray test plan id", required=True)
    parser.add_argument("-b", "--build", type=str,
                        help="Build number", required=True)
    parser.add_argument("-br", "--build_branch", type=str, default='stable',
                        help="Build branch (stable/main)", required=True)
    parser.add_argument("-s", "--setup_type", type=str, default='default',
                        help="Setup type (default/nearfull/isolated)", required=True)
    parser.add_argument("-c", "--comment_jira", type=str,
                        help="Test id where comments to be added")
    parser.add_argument("-st", "--skip_te", nargs='+', type=str,
                        help="Space separated list of TEs to skip from execution")
    parser.add_argument("-p", "--platform", type=str, default='VM_HW',
                        help="For which environment test plan needs to be created: VM/HW/OVA")
    parser.add_argument("-n", "--nodes", type=str,
                        help="Number of nodes in target: 1/3/N", default='', required=True)
    parser.add_argument("-sr", "--server_type", type=str,
                        help="Server type: HPC/DELL/SMC", required=True)
    parser.add_argument("-e", "--enclosure_type", type=str, default='5U84',
                        help="Enclosure type: 5U84/PODS/JBOD", required=True)
    parser.add_argument("-a", "--affect_version", type=str, default='LR-R2',
                        help="Affects Versions: LR-R2 or LR1.0 or LR1.0.1​")
    parser.add_argument("-f", "--fix_version", type=str, default='LR-R2',
                        help="Fix Versions: LR-R2 or LR1.0 or LR1.0.1​")
    parser.add_argument("-pf", "--product_family", type=str, default='LR', help="LR or K8")
    parser.add_argument("-sc", "--skip_te_clone", nargs='+', type=str,
                        help="Space separated te tickets to skip from cloning")
    parser.add_argument("-tc", "--tes_to_clone", nargs='+', type=str,
                        help="Space separated te tickets to clone")
    parser.add_argument("-tl", "--tp_labels", nargs='+', type=str,
                        help="Space separated labels for test plan")
    parser.add_argument("-cc", "--core_category", type=str, default='NA',
                        help="gold/silver")
    return parser.parse_args()


if __name__ == '__main__':
    opts = parse_args()
    main(opts)
