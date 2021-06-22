pipeline {
	agent {
        node {
			label 'ssc-vm-5613'
 			customWorkspace "/root/workspace/${JOB_BASE_NAME}"
		}
    }
    stages {
		stage('CODE_CHECKOUT') {
			steps{
			    checkout([$class: 'GitSCM', branches: [[name: '*/dev']], doGenerateSubmoduleConfigurations: false, extensions: [], submoduleCfg: [], userRemoteConfigs: [[credentialsId: 'rel_sanity_github_auto', url: 'https://github.com/Seagate/cortx-test/']]])
			}
		}
		stage('ENV_SETUP') {
			steps{
			    echo "${WORKSPACE}"
			    sh label: '', script: '''sh scripts/jenkins_job/virt_env_setup.sh . venv
source venv/bin/activate
python --version
export ADMIN_USR="${ADMIN_USR}"
export ADMIN_PWD="${ADMIN_PWD}"
export HOSTNAME="${HOSTNAME}"
export MGMT_VIP="${MGMT_VIP}"
export HOST_PASS="${HOST_PASS}"
python3.7 setup.py install
python3.7 setup.py develop
rm -rf build/
deactivate
'''
			}
		}
		stage('CLIENT_CONFIG') {
			steps{
			    sh label: '', script: '''source venv/bin/activate
python3.7 scripts/jenkins_job/multinode_server_client_setup.py "${HOST1}" "${HOST2}" "${HOST3}" --password "${HOST_PASS}" --mgmt_vip "${MGMT_VIP}"
deactivate
'''
			}
		}
		stage('CSM_Boarding') {
			steps{
			    sh label: '', script: '''source venv/bin/activate
python -m unittest scripts.jenkins_job.cortx_pre_onboarding.CSMBoarding.test_preboarding
python -m unittest scripts.jenkins_job.cortx_pre_onboarding.CSMBoarding.test_onboarding
deactivate
'''
			}
		}

		stage('TEST_EXECUTION') {
			steps{
			    sh label: '', script: '''source venv/bin/activate
sh scripts/jenkins_job/run_tests.sh
deactivate
'''
			}
		}
    }
	post {
		always {
			catchError(stageResult: 'FAILURE') {
			    archiveArtifacts allowEmptyArchive: true, artifacts: 'log/latest/results.xml, log/latest/results.html', followSymlinks: false
			    junit allowEmptyResults: true, testResults: 'log/latest/results.xml'
				emailext body: '${SCRIPT, template="REL_QA_SANITY_CUS_EMAIL_2.template"}', subject: '$PROJECT_NAME on Build # $CORTX_BUILD - $BUILD_STATUS!', to: 'nitesh.mahajan@seagate.com, dhananjay.dandapat@seagate.com, sonal.kalbende@seagate.com'
			}
		}
	}
}
