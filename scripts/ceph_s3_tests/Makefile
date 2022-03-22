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

# This file will setup & configure the ceph/s3-tests repo.
# Commands:
#	1. make help # To check supported tools by this script.
#	2. make setup-s3tests # Clone and setup s3-tests repo under cortx-test
#	3. make configure-s3tests  # Generate configuration file for running tests
# Note: Please provide existing s3account user access, secret keys through command line.

CORTX_TESTS_DIR=/root/makefile_test
ENDPOINT=s3.seagate.com
PORT_NUM=30443
REGION=default
USE_SSL=True
VALIDATE_CERTS=True
CA_CRT=/etc/ssl/stx-s3-clients/s3/ca.crt
BUCKET_PREFIX="cortxrgw-{random}-"
S3_MAIN_DN=None
S3_MAIN_UID=None
S3_MAIN_AK=None
S3_MAIN_SK=None
S3_ALT_UID=None
S3_ALT_AK=None
S3_ALT_SK=None
S3_TENANT_DN=None
S3_TENANT_UID=None
S3_TENANT_AK=None
S3_TENANT_SK=None

s3tests_dir = $(CORTX_TESTS_DIR)/s3-tests
s3test_conf_file=$(s3tests_dir)/s3tests.conf
s3test_conf_template=$(CORTX_TESTS_DIR)/ceph_s3_tests/cortx_rgw_template.conf

setup-s3tests:

	@echo "### Clone and setup s3-tests. ###"
	rm -rf $(s3tests_dir)
	cd $(CORTX_TESTS_DIR) && git clone https://github.com/ceph/s3-tests
	cd $(s3tests_dir) && sh bootstrap virtualenv="python3.6 -m venv"
	@echo "### Setup for s3-tests complete. ###"

configure-s3tests:

	@echo "### Generate s3-tests conf file. ###"
	cp $(s3test_conf_template) $(s3test_conf_file)
	sed -i 's|ENDPOINT|$(ENDPOINT)|g' $(s3test_conf_file)
	sed -i 's|PORT_NUM|$(PORT_NUM)|g' $(s3test_conf_file)
	sed -i 's|REGION|$(REGION)|g' $(s3test_conf_file)
	sed -i 's|BUCKET_PREFIX|$(BUCKET_PREFIX)|g' $(s3test_conf_file)
	sed -i 's|USE_SSL|$(USE_SSL)|g' $(s3test_conf_file)
	sed -i 's|VALIDATE_CERTS|$(VALIDATE_CERTS)|g' $(s3test_conf_file)
	sed -i 's|S3_MAIN_DN|$(S3_MAIN_DN)|g' $(s3test_conf_file)
	sed -i 's|S3_MAIN_UID|$(S3_MAIN_UID)|g' $(s3test_conf_file)
	sed -i 's|S3_MAIN_AK|$(S3_MAIN_AK)|g' $(s3test_conf_file)
	sed -i 's|S3_MAIN_SK|$(S3_MAIN_SK)|g' $(s3test_conf_file)
	sed -i 's|S3_ALT_DN|$(S3_ALT_DN)|g' $(s3test_conf_file)
	sed -i 's|S3_ALT_UID|$(S3_ALT_UID)|g' $(s3test_conf_file)
	sed -i 's|S3_ALT_AK|$(S3_ALT_AK)|g' $(s3test_conf_file)
	sed -i 's|S3_ALT_SK|$(S3_ALT_SK)|g' $(s3test_conf_file)
	sed -i 's|S3_TENANT_DN|$(S3_TENANT_DN)|g' $(s3test_conf_file)
	sed -i 's|S3_TENANT_UID|$(S3_TENANT_UID)|g' $(s3test_conf_file)
	sed -i 's|S3_TENANT_AK|$(S3_TENANT_AK)|g' $(s3test_conf_file)
	sed -i 's|S3_TENANT_SK|$(S3_TENANT_SK)|g' $(s3test_conf_file)
	@echo "### Generated s3-tests conf file. ###"

clean:

	@echo "### Cleanup s3-tests. ###"
	rm -rf $(s3tests_dir)
	@echo "### Cleanup for s3-tests complete. ###"

help :

	@echo "all: Clone s3-tests repo, setup requirements and generate configuration file"
	@echo "clean: Cleanup s3-tests directory"
	@echo "setup-s3tests: Clone and setup s3-tests repo under cortx-test directory"
	@echo "configure-s3tests: Generate configuration file for running tests"
