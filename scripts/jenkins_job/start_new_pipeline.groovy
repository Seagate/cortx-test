#!/usr/bin/env groovy
pipeline {
	agent {
        node {
			label 'ssc-vm-3053'
			customWorkspace '/root/workspace/cortx-test/${JOB_NAME}_${BUILD_NUMBER}'

		}
    }
    stages {
		stage('REL_SANITY') {
			steps{
				script{
					catchError(stageResult: 'FAILURE') {
						def remote = [:]
						remote.name = "${HOSTNAME}"
						remote.host = "${HOSTNAME}"
						remote.user = 'root'
						remote.password = "${HOST_PASS}"
						remote.allowAnyHosts = true
						remote.fileTransfer = 'scp'
				// 		remote.logLevel = 'INFO'

						withCredentials([sshUserPrivateKey(credentialsId: '8dc7ea49-f2d8-484f-9579-679914429d64', keyFileVariable: 'FILE', passphraseVariable: 'passphrase', usernameVariable: 'username')]) {
							sshPut remote: remote, from: "${FILE}", into: '~/.ssh/my-key'
							sshCommand remote: remote, command: 'chmod 600 ~/.ssh/my-key'
							//sshCommand remote: remote, command: 'rm -rf ~/eos-test'
							//sshCommand remote: remote, command: 'echo -e "Host seagit.okla.seagate.com\n\tStrictHostKeyChecking no\n" >> ~/.ssh/config'
							sshCommand  command: 'eval "$(ssh-agent)"; ssh-agent $(ssh-add /root/.ssh/my-key); git clone -b eos-19246-new-pipeline https://github.com/Seagate/cortx-test.git'
						}
						requirements, vir
						source venv/bin/activate
						//python3.7 setup.py install
                        //python3.7 setup.py develop
						setup
						//sshCommand remote: remote, command: 'cd /root/eos-test; python3.6 scripts/DevOPs/setup_client.py > setup_client.log'
						def mytext = """set -e

set -v
cd /root/eos-test
#source venv/bin/activate
export ADMIN_USR="${ADMIN_USR}"
export ADMIN_PWD="${ADMIN_PWD}"
export HOST_PASS="${HOST_PASS}"
//python3.7 setup.py install
//python3.7 setup.py develop
client_conf
mkdir -p cortx_logs
ln -sf /root/workspace/cortx-test/log/latest/ cortx_logs/
python -m unittest scripts.DevOPs.csm_boarding.CSMBoarding.test_preboarding
python -m unittest scripts.DevOPs.csm_boarding.CSMBoarding.test_onboarding
#avocado run tests/test_release_sanity_bvt.py --filter-by-tags healthcheck
#avocado run tests/test_release_sanity_bvt.py || true
run_test.sh --target $host
pytest tests/s3/test_object_tagging.py::TestObjectTagging --local True --target ssc-vm-3031
deactivate

"""
						writeFile file: 'run.sh', text: mytext
						sshScript remote: remote, script: "run.sh"
						sshGet remote: remote, from: '~/eos-test/avocado_logs/latest/results.xml', into: 'results.xml', override: true
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