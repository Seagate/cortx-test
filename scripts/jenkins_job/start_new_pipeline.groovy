pipeline {
	agent {
        node {
			label 'ssc-vm-3053'
 			customWorkspace "/root/workspace/${JOB_BASE_NAME}"
		}
    }
    stages {
		stage('CODE_CHECKOUT') {
			steps{
			    checkout([$class: 'GitSCM', branches: [[name: '*/eos-19246-new-pipeline']], doGenerateSubmoduleConfigurations: false, extensions: [], submoduleCfg: [], userRemoteConfigs: [[credentialsId: 'rel_sanity_github_auto', url: 'https://github.com/sonalk0209/cortx-test/']]])
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
python3.7 setup.py install
python3.7 setup.py develop
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
			    //junit allowEmptyResults: true, testResults: 'log/latest/results.xml'
				//emailext body: '${SCRIPT, template="REL_QA_SANITY_CUS_EMAIL.template"}', subject: '$PROJECT_NAME on Build # $CORTX_BUILD - $BUILD_STATUS!', to: 'nitesh.mahajan@seagate.com, dhananjay.dandapat@seagate.com, sonal.kalbende@seagate.com'
			}
		}
	}
}
