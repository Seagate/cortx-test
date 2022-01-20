pipeline {
	agent {
        node {
			label "${CLIENT_NODE}"
 			customWorkspace "/root/workspace/${JOB_BASE_NAME}"
		}
    }
    environment {
		Target_Node = 'three-node-' + "${"${HOST1}".split("\\.")[0]}"
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
export HOST_PASS="${HOST_PASS}"
export Target_Node="${Target_Node}"
deactivate
'''
			}
		}
		stage('CLIENT_CONFIG') {
			steps{
			    sh label: '', script: '''source venv/bin/activate
export PYTHONPATH=$WORKSPACE:$PYTHONPATH
echo $PYTHONPATH
python3.7 scripts/jenkins_job/multinode_server_client_setup.py "${HOST1}" "${HOST2}" "${HOST3}" --node_count 3 --password "${HOST_PASS}" --mgmt_vip "${MGMT_VIP}"
deactivate
'''
			}
		}
		stage('CSM_Boarding') {
			steps{
			    sh label: '', script: '''source venv/bin/activate
export MGMT_VIP="${MGMT_VIP}"
pytest scripts/jenkins_job/aws_configure.py::test_preboarding --local True --target ${Target_Node}
deactivate
'''
			}
		}

		stage('TEST_EXECUTION') {
			steps{
			    sh label: '', script: '''source venv/bin/activate
export Target_Node="${Target_Node}"
sh comptests/prov/run_lc_tests.sh ${Target_Node}
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
