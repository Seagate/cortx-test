pipeline {
	agent {
        node {
			label "${CLIENT_NODE}"
 			customWorkspace "/root/workspace/${JOB_BASE_NAME}"
		}
    }
    environment {
		Target_Node = "${"${HOSTNAME}".split("\\.")[0]}"
    }
    stages {
		stage('CODE_CHECKOUT') {
			steps{
			    cleanWs()
			    checkout([$class: 'GitSCM', branches: [[name: '*/dev']], doGenerateSubmoduleConfigurations: false, extensions: [], submoduleCfg: [], userRemoteConfigs: [[credentialsId: 'rel_sanity_github_auto', url: 'https://github.com/Seagate/cortx-test.git']]])
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
export HOST_PASS="${HOST_PASS}"
export Target_Node="${Target_Node}"
rm -rf build/
deactivate
'''
			}
		}
		stage('CLIENT_CONFIG') {
			steps{
			    sh label: '', script: '''source venv/bin/activate
python3.7 scripts/jenkins_job/client_conf.py
deactivate
'''
			}
		}
		stage('CSM_Boarding') {
			steps{
			    sh label: '', script: '''source venv/bin/activate
export MGMT_VIP="${HOSTNAME}"
pytest scripts/jenkins_job/aws_configure.py::test_preboarding --local True --target ${Target_Node}
deactivate
'''
			}
		}

		stage('TEST_EXECUTION') {
			steps{
			    sh label: '', script: '''source venv/bin/activate
export HOSTNAME="${HOSTNAME}"
sh scripts/jenkins_job/run_tests.sh
deactivate
'''
			}
		}
    }
	post {
		always {
			catchError(stageResult: 'FAILURE') {
			    archiveArtifacts allowEmptyArchive: true, artifacts: 'log/latest/results.xml, log/latest/results.html, *.png', followSymlinks: false
			    junit allowEmptyResults: true, testResults: 'log/latest/results.xml'
				emailext body: '${SCRIPT, template="REL_QA_SANITY_CUS_EMAIL.template"}', recipientProviders: [requestor()], subject: '$PROJECT_NAME on Build # $CORTX_BUILD - $BUILD_STATUS!', to: "${EMAIL_RECEPIENTS}"
			}
		}
	}
}
