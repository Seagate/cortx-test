#!/usr/bin/env python3
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

""" Script to change copyright headers"""
import os

"""
Find files with following command

cd $project_root; find . -type f -name "*.py" -exec egrep -l '# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
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
#' {} \;
"""
files = [
    './cortx-test/tests/blackbox/test_minio_client.py',
    './cortx-test/tests/blackbox/test_s3fs.py',
    './cortx-test/tests/blackbox/test_cortxcli.py',
    './cortx-test/tests/blackbox/test_jcloud_jclient.py',
    './cortx-test/tests/blackbox/test_aws_iam.py',
    './cortx-test/tests/blackbox/test_aws_cli_s3api.py',
    './cortx-test/tests/blackbox/test_s3cmd.py',
    './cortx-test/tests/csm/cli/test_cli_system_.py',
    './cortx-test/tests/csm/cli/test_cli_alerts.py',
    './cortx-test/tests/csm/cli/test_cli_security.py',
    './cortx-test/tests/csm/cli/test_cli_s3_accounts.py',
    './cortx-test/tests/csm/cli/test_iam_users.py',
    './cortx-test/tests/csm/cli/test_cli_buckets.py',
    './cortx-test/tests/csm/cli/test_cli_csm_user.py',
    './cortx-test/tests/csm/cli/test_cli_bucket_policy.py',
    './cortx-test/tests/csm/cli/test_cli_support_bundle.py',
    './cortx-test/tests/csm/gui/test_server_os_gui_alerts.py',
    './cortx-test/tests/csm/rest/test_audit_logs.py',
    './cortx-test/tests/csm/rest/test_s3_users.py',
    './cortx-test/tests/csm/rest/test_system_stats.py',
    './cortx-test/tests/csm/rest/test_system_health.py',
    './cortx-test/tests/csm/rest/test_bucket_policy.py',
    './cortx-test/tests/csm/rest/test_bucket.py',
    './cortx-test/tests/csm/rest/test_csm_users.py',
    './cortx-test/tests/csm/rest/test_capacity_usage.py',
    './cortx-test/tests/csm/rest/test_iam_users.py',
    './cortx-test/tests/csm/rest/test_csm_load.py',
    './cortx-test/tests/csm/rest/test_csm_alerts.py',
    './cortx-test/tests/load_test/test_s3_load.py',
    './cortx-test/tests/prov/test_sw_update_disruptive.py',
    './cortx-test/tests/prov/test_post_deploy_validation.py',
    './cortx-test/tests/prov/test_prov_single_node.py',
    './cortx-test/tests/prov/test_prov_post_deploy_commands.py',
    './cortx-test/tests/prov/test_prov_three_node.py',
    './cortx-test/tests/cft/test_s3bench_workload.py',
    './cortx-test/tests/cft/test_intel_isa_workload.py',
    './cortx-test/tests/cft/test_r2_support_bundle.py',
    './cortx-test/tests/cft/test_deploy_node_health.py',
    './cortx-test/tests/cft/test_failure_domain.py',
    './cortx-test/tests/cft/test_system_limit.py',
    './cortx-test/tests/ras/test_server_os.py',
    './cortx-test/tests/ras/test_bmc_faults.py',
    './cortx-test/tests/ras/test_storage_enclosure_fru_alerts.py',
    './cortx-test/tests/ras/test_sspl_secondary.py',
    './cortx-test/tests/ras/test_raid_operations.py',
    './cortx-test/tests/ras/test_sspl.py',
    './cortx-test/tests/ras/test_3ps_monitoring.py',
    './cortx-test/tests/ras/test_3ps_monitoring_gui.py',
    './cortx-test/tests/ras/test_network_faults.py',
    './cortx-test/tests/ras/test_server_fru_alerts.py',
    './cortx-test/tests/s3/test_audit_logs.py',
    './cortx-test/tests/s3/test_delete_account_temp_cred.py',
    './cortx-test/tests/s3/test_bucket_tagging.py',
    './cortx-test/tests/s3/test_multipart_abort_copy.py',
    './cortx-test/tests/s3/test_iam_user_login.py',
    './cortx-test/tests/s3/test_iam_user_management.py',
    './cortx-test/tests/s3/test_object_workflow_operations.py',
    './cortx-test/tests/s3/test_s3_account_user_management_reset_password.py',
    './cortx-test/tests/s3/test_object_acl.py',
    './cortx-test/tests/s3/test_bucket_policy.py',
    './cortx-test/tests/s3/test_list_object_v2_using_aws_s3_api.py',
    './cortx-test/tests/s3/test_iam_account_login.py',
    './cortx-test/tests/s3/test_copy_object.py',
    './cortx-test/tests/s3/test_all_users_bucket_acl.py',
    './cortx-test/tests/s3/test_s3_faulttolerance.py',
    './cortx-test/tests/s3/test_put_bucket.py',
    './cortx-test/tests/s3/test_openldap.py',
    './cortx-test/tests/s3/test_bucket_location.py',
    './cortx-test/tests/s3/test_multipart_upload.py',
    './cortx-test/tests/s3/test_dos_scalability.py',
    './cortx-test/tests/s3/multipart_upload/test_multipart_delete.py',
    './cortx-test/tests/s3/test_account_user_management.py',
    './cortx-test/tests/s3/test_bucket_workflow_operations.py',
    './cortx-test/tests/s3/test_all_users_object_acl.py',
    './cortx-test/tests/s3/test_object_tagging.py',
    './cortx-test/tests/s3/test_delayed_delete.py',
    './cortx-test/tests/s3/test_object_metadata_operations.py',
    './cortx-test/tests/s3/test_data_durability.py',
    './cortx-test/tests/s3/test_data_path_validation.py',
    './cortx-test/tests/s3/test_s3_concurrency.py',
    './cortx-test/tests/s3/test_authserver_healthcheck.py',
    './cortx-test/tests/s3/test_multipart_getput.py',
    './cortx-test/tests/s3/test_support_bundle.py',
    './cortx-test/tests/s3/test_s3_account_mgmt_delete_user_generate_access_key.py',
    './cortx-test/tests/s3/test_bucket_acl.py',
    './cortx-test/tests/di/test_di.py',
    './cortx-test/tests/di/test_di_with_s3_params.py',
    './cortx-test/tests/di/test_di_durability.py',
    './cortx-test/tests/ha/test_ha_cluster_health.py',
    './cortx-test/tests/ha/test_ha_node_health.py',
    './cortx-test/tests/ha/test_ha_node_failure.py',
    './cortx-test/tests/ha/test_ha_node_health_gui.py',
    './cortx-test/tests/ha/test_ha_node_stop_start.py',
    './cortx-test/tests/ha/test_ha_cluster_health_gui.py',
    './cortx-test/libs/csm/cli/cortx_cli_system.py',
    './cortx-test/libs/csm/cli/cli_csm_user.py',
    './cortx-test/libs/csm/cli/cortx_cli_bucket_policy.py',
    './cortx-test/libs/csm/cli/cortx_cli_s3_buckets.py',
    './cortx-test/libs/csm/cli/cortx_cli_s3_accounts.py',
    './cortx-test/libs/csm/cli/cortx_cli.py',
    './cortx-test/libs/csm/cli/cortxcli_iam_user.py',
    './cortx-test/libs/csm/cli/cli_alerts_lib.py',
    './cortx-test/libs/csm/cli/cortx_cli_s3access_keys.py',
    './cortx-test/libs/csm/cli/cortx_node_cli.py',
    './cortx-test/libs/csm/cli/cortx_cli_client.py',
    './cortx-test/libs/csm/cli/cortx_cli_support_bundle.py',
    './cortx-test/libs/csm/csm_setup.py',
    './cortx-test/libs/csm/rest/csm_rest_capacity.py',
    './cortx-test/libs/csm/rest/csm_rest_bucket.py',
    './cortx-test/libs/csm/rest/csm_rest_s3user.py',
    './cortx-test/libs/csm/rest/csm_rest_core_lib.py',
    './cortx-test/libs/csm/rest/csm_rest_system_health.py',
    './cortx-test/libs/csm/rest/csm_rest_test_lib.py',
    './cortx-test/libs/csm/rest/csm_rest_stats.py',
    './cortx-test/libs/csm/rest/csm_rest_alert.py',
    './cortx-test/libs/csm/rest/csm_rest_csmuser.py',
    './cortx-test/libs/csm/rest/csm_rest_iamuser.py',
    './cortx-test/libs/csm/rest/csm_rest_audit_logs.py',
    './cortx-test/libs/prov/prov_upgrade.py',
    './cortx-test/libs/prov/provisioner.py',
    './cortx-test/libs/prov/prov_deploy_ff.py',
    './cortx-test/libs/ras/sw_alerts.py',
    './cortx-test/libs/ras/sw_alerts_gui.py',
    './cortx-test/libs/ras/ras_core_lib.py',
    './cortx-test/libs/ras/ras_test_lib.py',
    './cortx-test/libs/s3/s3_tagging_test_lib.py',
    './cortx-test/libs/s3/s3_core_lib.py',
    './cortx-test/libs/s3/csm_rest_cli_interface_lib.py',
    './cortx-test/libs/s3/s3_restapi_test_lib.py',
    './cortx-test/libs/s3/iam_core_lib.py',
    './cortx-test/libs/s3/s3_cmd_test_lib.py',
    './cortx-test/libs/s3/s3_multipart_test_lib.py',
    './cortx-test/libs/s3/cortxcli_test_lib.py',
    './cortx-test/libs/s3/iam_test_lib.py',
    './cortx-test/libs/s3/csm_restapi_interface_lib.py',
    './cortx-test/libs/s3/s3_rest_cli_interface_lib.py',
    './cortx-test/libs/s3/s3_bucket_policy_test_lib.py',
    './cortx-test/libs/s3/s3_test_lib.py',
    './cortx-test/libs/s3/s3_acl_test_lib.py',
    './cortx-test/libs/s3/s3_common_test_lib.py',
    './cortx-test/libs/s3/__init__.py',
    './cortx-test/libs/jmeter/jmeter_integration.py',
    './cortx-test/libs/motr/motr_test_lib.py',
    './cortx-test/libs/motr/__init__.py',
    './cortx-test/libs/di/di_data_correction_test_lib.py',
    './cortx-test/libs/di/uploader.py',
    './cortx-test/libs/di/di_params.py',
    './cortx-test/libs/di/data_generator.py',
    './cortx-test/libs/di/data_man.py',
    './cortx-test/libs/di/di_test_framework.py',
    './cortx-test/libs/di/di_constants.py',
    './cortx-test/libs/di/file_formats.py',
    './cortx-test/libs/di/downloader.py',
    './cortx-test/libs/di/di_base.py',
    './cortx-test/libs/di/di_lib.py',
    './cortx-test/libs/di/di_buckets.py',
    './cortx-test/libs/di/di_feature_control.py',
    './cortx-test/libs/di/di_run_man.py',
    './cortx-test/libs/di/di_error_detection_test_lib.py',
    './cortx-test/libs/di/di_mgmt_ops.py',
    './cortx-test/libs/di/di_destructive_step.py',
    './cortx-test/libs/di/fi_adapter.py',
    './cortx-test/libs/di/__init__.py',
    './cortx-test/libs/ha/ha_common_libs.py',
    './cortx-test/libs/ha/ha_common_libs_gui.py',
    './cortx-test/config/s3/__init__.py',
    './cortx-test/config/__init__.py',
    './cortx-test/switch_setup.py',
    './cortx-test/robot_testrunner.py',
    './cortx-test/robot_gui/cicd/csm_test.py',
    './cortx-test/robot_gui/resources/common/element_locators.py',
    './cortx-test/robot_gui/resources/common/common_variables.py',
    './cortx-test/robot_gui/utils/call_robot_test.py',
    './cortx-test/robot_gui/utils/create-SSL.py',
    './cortx-test/robot_gui/utils/Download.py',
    './cortx-test/comptests/prov/test_prov_nodeadmin_prompt.py',
    './cortx-test/comptests/prov/test_prov_deploy_ff_commands.py',
    './cortx-test/comptests/motr/test_motr_workloads.py',
    './cortx-test/comptests/motr/test_s3_workload_motr.py',
    './cortx-test/core/locking_server.py',
    './cortx-test/core/report_rpc.py',
    './cortx-test/core/producer.py',
    './cortx-test/core/rpcserver.py',
    './cortx-test/core/health_status_check_update.py',
    './cortx-test/core/runner.py',
    './cortx-test/core/client_config.py',
    './cortx-test/core/kafka_consumer.py',
    './cortx-test/unittests/test_requirement_testcase_specific_logs.py',
    './cortx-test/unittests/test_pytest_features.py',
    './cortx-test/unittests/helpers/test_s3_helpers.py',
    './cortx-test/unittests/helpers/test_node_health_helpers.py',
    './cortx-test/unittests/helpers/test_node_helper.py',
    './cortx-test/unittests/test_di_sample.py',
    './cortx-test/unittests/test_ras_test_lib.py',
    './cortx-test/unittests/test_timings_demo.py',
    './cortx-test/unittests/s3/test_s3_bucket_policy_test_lib.py',
    './cortx-test/unittests/s3/test_s3_multipart_test_lib.py',
    './cortx-test/unittests/s3/test_s3_test_lib.py',
    './cortx-test/unittests/s3/test_s3_rest_cli_interface_lib.py',
    './cortx-test/unittests/s3/test_s3_tagging_test_lib.py',
    './cortx-test/unittests/s3/test_s3_cmd_test_lib.py',
    './cortx-test/unittests/s3/test_iam_test_lib.py',
    './cortx-test/unittests/s3/test_s3_acl_test_lib.py',
    './cortx-test/unittests/s3/test_s3_restapi_test_lib.py',
    './cortx-test/unittests/test_ordering.py',
    './cortx-test/unittests/test_csm_rest.py',
    './cortx-test/unittests/scripts/s3_bench/test_s3bench_ut.py',
    './cortx-test/unittests/test_reporting_and_logging_hooks.py',
    './cortx-test/unittests/test_random_alert_generation.py',
    './cortx-test/unittests/test_serverlogs_helper.py',
    './cortx-test/unittests/utils/test_s3_utils.py',
    './cortx-test/commons/configmanager.py',
    './cortx-test/commons/alerts_simulator/generate_alert_wrappers.py',
    './cortx-test/commons/alerts_simulator/generate_alert_lib.py',
    './cortx-test/commons/alerts_simulator/constants.py',
    './cortx-test/commons/alerts_simulator/random_alerts/teardown_lib.py',
    './cortx-test/commons/alerts_simulator/random_alerts/constants_random_alert_generation.py',
    './cortx-test/commons/alerts_simulator/random_alerts/random_alert_generation.py',
    './cortx-test/commons/errorcodes.py',
    './cortx-test/commons/s3_dns.py',
    './cortx-test/commons/timings_client.py',
    './cortx-test/commons/helpers/salt_helper.py',
    './cortx-test/commons/helpers/controller_helper.py',
    './cortx-test/commons/helpers/bmc_helper.py',
    './cortx-test/commons/helpers/host.py',
    './cortx-test/commons/helpers/s3_helper.py',
    './cortx-test/commons/helpers/health_helper.py',
    './cortx-test/commons/helpers/node_helper.py',
    './cortx-test/commons/helpers/serverlogs_helper.py',
    './cortx-test/commons/helpers/telnet_helper.py',
    './cortx-test/commons/pswdmanager.py',
    './cortx-test/commons/greenlet_worker.py',
    './cortx-test/commons/commands.py',
    './cortx-test/commons/worker.py',
    './cortx-test/commons/Globals.py',
    './cortx-test/commons/ct_fail_on.py',
    './cortx-test/commons/params.py',
    './cortx-test/commons/conftest.py',
    './cortx-test/commons/datatypes.py',
    './cortx-test/commons/constants.py',
    './cortx-test/commons/exceptions.py',
    './cortx-test/commons/utils/deploy_utils.py',
    './cortx-test/commons/utils/web_utils.py',
    './cortx-test/commons/utils/system_utils.py',
    './cortx-test/commons/utils/assert_utils.py',
    './cortx-test/commons/utils/support_bundle_utils.py',
    './cortx-test/commons/utils/config_utils.py',
    './cortx-test/commons/utils/jira_utils.py',
    './cortx-test/commons/utils/s3_utils.py',
    './cortx-test/commons/report_client.py',
    './cortx-test/drunner.py',
    './cortx-test/conftest.py',
    './cortx-test/testrunner.py',
    './cortx-test/scripts/ssc_cloud/service_account_access.py',
    './cortx-test/scripts/ssc_cloud/vm_management.py',
    './cortx-test/scripts/ssc_cloud/ssc_vm_ops.py',
    './cortx-test/scripts/k8s_cluster_setup/deploy_k8s.py',
    './cortx-test/scripts/jenkins_job/aws_configure.py',
    './cortx-test/scripts/jenkins_job/client_conf.py',
    './cortx-test/scripts/jenkins_job/multinode_server_client_setup.py',
    './cortx-test/scripts/jenkins_job/cortx_pre_onboarding.py',
    './cortx-test/scripts/jenkins_job/trigger_jenkins_job.py',
    './cortx-test/scripts/s3_bench/s3bench.py',
    './cortx-test/scripts/locust/locust_utils.py',
    './cortx-test/scripts/locust/locustfile.py',
    './cortx-test/scripts/locust/locustfile_step_users.py',
    './cortx-test/scripts/locust/locust_runner.py',
    './cortx-test/scripts/s3_tools/create_s3_account.py',
    './cortx-test/scripts/server_scripts/encryptor.py',
    './cortx-test/scripts/server_scripts/telnet_operations.py',
    './cortx-test/scripts/server_scripts/rabbitmq_reader.py',
    './cortx-test/scripts/server_scripts/read_message_bus.py',
    './cortx-test/tools/cmi_calc.py',
    './cortx-test/tools/rest_server/app.py',
    './cortx-test/tools/rest_server/rest_app/timings_api.py',
    './cortx-test/tools/rest_server/rest_app/mongodbapi.py',
    './cortx-test/tools/rest_server/rest_app/read_config.py',
    './cortx-test/tools/rest_server/rest_app/test_execution_api.py',
    './cortx-test/tools/rest_server/rest_app/systems_api.py',
    './cortx-test/tools/rest_server/rest_app/vm_pool_api.py',
    './cortx-test/tools/rest_server/rest_app/validations.py',
    './cortx-test/tools/rest_server/rest_app/cmi_api.py',
    './cortx-test/tools/setup_update/setup_entry.py',
    './cortx-test/tools/db_update.py',
    './cortx-test/tools/clone_test_plan/jira_api.py',
    './cortx-test/tools/clone_test_plan/clone_test_plan.py',
    './cortx-test/tools/datagen/generate_dataset.py',
    './cortx-test/tools/report/exec_report_pdf.py',
    './cortx-test/tools/report/jira_api.py',
    './cortx-test/tools/report/common_pdf.py',
    './cortx-test/tools/report/engg_report_csv.py',
    './cortx-test/tools/report/engg_report_pdf.py',
    './cortx-test/tools/report/exec_report_csv.py',
    './cortx-test/tools/report/common.py',
    './cortx-test/tools/report/mongodb_api.py',
    './cortx-test/tools/dash_server/perfdbAPIs.py',
    './cortx-test/tools/dash_server/query_tab_layout.py',
    './cortx-test/tools/dash_server/timingAPIs.py',
    './cortx-test/tools/dash_server/R2_callbacks/engg_report_callbacks.py',
    './cortx-test/tools/dash_server/R2_callbacks/exe_report_callbacks.py',
    './cortx-test/tools/dash_server/mongodbAPIs.py',
    './cortx-test/tools/dash_server/Common_callbacks/main_page_callbacks.py',
    './cortx-test/tools/dash_server/Common_callbacks/defect_list_tab_callbacks.py',
    './cortx-test/tools/dash_server/Common_callbacks/query_tab_callbacks.py',
    './cortx-test/tools/dash_server/qa_tab_layouts.py',
    './cortx-test/tools/dash_server/main_app.py',
    './cortx-test/tools/dash_server/Performance/schemas.py',
    './cortx-test/tools/dash_server/Performance/graphs/graphs_dropdown_callbacks.py',
    './cortx-test/tools/dash_server/Performance/graphs/graphs_callbacks.py',
    './cortx-test/tools/dash_server/Performance/graphs/graphs_layouts.py',
    './cortx-test/tools/dash_server/Performance/styles.py',
    './cortx-test/tools/dash_server/Performance/statistics/statistics_layouts.py',
    './cortx-test/tools/dash_server/Performance/statistics/stats_dropdown_callbacks.py',
    './cortx-test/tools/dash_server/Performance/statistics/statistics_callbacks.py',
    './cortx-test/tools/dash_server/Performance/statistics/degraded_read.py',
    './cortx-test/tools/dash_server/Performance/perf_main.py',
    './cortx-test/tools/dash_server/Performance/global_functions.py',
    './cortx-test/tools/dash_server/Performance/backend.py',
    './cortx-test/tools/dash_server/Performance/mongodb_api.py',
    './cortx-test/tools/dash_server/common.py',
    './cortx-test/tools/dash_server/R1_callbacks/r1_engg_report_callbacks.py',
    './cortx-test/tools/dash_server/R1_callbacks/r1_exe_report_callbacks.py'
]

new_copyright = """# Copyright (c) 2022 Seagate Technology LLC and/or its Affiliates
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
"""
old_copyright = """# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
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
"""

check_headr = "# Copyright (c)"

new_copyright_for_blank = """#
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

def main():
    for filename in files:
        if os.path.exists(filename):
            try:
                f = open(filename, encoding='utf-8')
                data = f.read()
                f.close()
                i = data.find(old_copyright)
                if i < 0:
                    print('no change needed:', filename)
                    i = data.find(check_headr)
                    if i < 0:
                        data = new_copyright_for_blank + data[:]
                        new = filename + ".new"
                        backup = filename + ".bak"
                        f = open(new, "w")
                        f.write(data)
                        f.close()
                        os.rename(filename, backup)
                        os.rename(new, filename)
                        os.remove(backup)
                        print('Copyright message added for file with copyright %s' % (filename,))
                    continue

                data = data[:i] + new_copyright + data[i + len(old_copyright):]
                new = filename + ".new"
                backup = filename + ".bak"
                f = open(new, "w")
                f.write(data)
                f.close()
                os.rename(filename, backup)
                os.rename(new, filename)
                os.remove(backup)
                print('Copyright message added for %s' % (filename,))
            except Exception as fault:
                print(fault)


if __name__ == '__main__':
    main()
