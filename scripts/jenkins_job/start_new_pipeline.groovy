#!/usr/bin/env groovy
pipeline {
	agent {
        node {
			label 'ssc-vm-3053'
			customWorkspace '/root/workspace/${JOB_NAME}_${BUILD_NUMBER}'

		}
    }
    stages {
		stage('REL_SANITY') {
			steps{
				script{
					catchError(stageResult: 'FAILURE') {
						def remote = [:]
						remote.name = "ssc-vm-3053.colo.seagate.com"
						remote.host = "ssc-vm-3053.colo.seagate.com"
						remote.user = 'root'
						remote.password = "seagate"
						remote.allowAnyHosts = true
						remote.fileTransfer = 'scp'
				// 		remote.logLevel = 'INFO'

						withCredentials([usernamePassword(credentialsId: 'rel_sanity_github_auto', passwordVariable: 'password', usernameVariable: 'username')]) {
						sshCommand remote: remote, command: 'rm -rf ~/workspace/cortx_test'
						sshCommand  command: 'git clone -b eos-19246-new-pipeline https://$username:$password@github.com/$username/cortx-test.git'
						}

						def mytext = """set -e

set -v
cd /root/workspace/cortx-test/
sh scripts/jenkins_job/virt_env_setup.sh /root/workspace/cortx-test/ venv
source venv/bin/activate
export ADMIN_USR="${ADMIN_USR}"
export ADMIN_PWD="${ADMIN_PWD}"
export HOSTNAME="${HOSTNAME}"
export HOST_PASS="${HOST_PASS}"
python3.7 setup.py install
python3.7 setup.py develop
python3.7 scripts/jenkins_job/client_conf.py
//python -m unittest scripts.DevOPs.csm_boarding.CSMBoarding.test_preboarding
//python -m unittest scripts.DevOPs.csm_boarding.CSMBoarding.test_onboarding
//sh scripts/jenkins_job/run_pytest.sh --target $HOSTNAME
pytest tests/s3/test_object_tagging.py::TestObjectTagging --local True --target ssc-vm-2978 pytest --junitxml=/root/workspace/cortx-test/log/latest/
deactivate

"""
						writeFile file: 'run.sh', text: mytext
						sshScript remote: remote, script: "run.sh"
						sshGet remote: remote, from: '~/workspace/cortx-test/log/latest/results.xml', into: 'results.xml', override: true
					}
				}
			}
		}
    }
	post {
		always {
			catchError(stageResult: 'FAILURE') {
				junit allowEmptyResults: true, testResults: 'results.xml'
				emailext body: '${SCRIPT, template="REL_QA_SANITY_CUS_EMAIL.template"}', subject: '$PROJECT_NAME on Build # $CORTX_BUILD - $BUILD_STATUS!', to: 'nitesh.mahajan@seagate.com, dhananjay.dandapat@seagate.com, sonal.kalbende@seagate.com'
			}
		}
	}
}