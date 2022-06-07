pipeline {
	agent {
        node {
			label "${CLIENT_NODE}"
 			customWorkspace "/root/workspace/${JOB_BASE_NAME}"
		}
    }
    environment {
		Target_Node = 'multi-node-' + "${"${M_NODE}".split("\\.")[0]}"
		WORK_SPACE = "/root/workspace/${JOB_BASE_NAME}"
    }
    stages {
		stage('CODE_CHECKOUT') {
			steps{
			    cleanWs()
			    checkout([$class: 'GitSCM', branches: [[name: '*/main']], doGenerateSubmoduleConfigurations: false, extensions: [], submoduleCfg: [], userRemoteConfigs: [[credentialsId: 'rel_sanity_github_auto', url: 'https://github.com/Seagate/cortx-test.git']]])
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
export WORK_SPACE="${WORK_SPACE}"
export EXTERNAL_EXPOSURE_SERVICE="${EXTERNAL_EXPOSURE_SERVICE}"
deactivate
'''
			}
		}
		stage('CLIENT_CONFIG') {
			steps{
			    sh label: '', script: '''source venv/bin/activate
export PYTHONPATH=$WORKSPACE:$PYTHONPATH
echo $PYTHONPATH
sh scripts/cicd_k8s/lb_haproxy.sh
python3.7 scripts/cicd_k8s/client_multinode_rgw.py --master_node "${M_NODE}" --password "${HOST_PASS}"
deactivate
'''
			}
		}
		stage('TEST_EXECUTION') {
			steps{
			    sh label: '', script: '''source venv/bin/activate
export PYTHONPATH=$WORKSPACE:$PYTHONPATH
echo $PYTHONPATH
export Target_Node="${Target_Node}"
export WORK_SPACE="${WORK_SPACE}"
sh comptests/prov/run_lc_tests.sh ${Target_Node} ${WORK_SPACE}
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
