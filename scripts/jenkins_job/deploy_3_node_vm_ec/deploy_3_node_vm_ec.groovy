pipeline {
	agent {
        node {
			label "${Client_Node}"
 			customWorkspace "/root/workspace/${JOB_BASE_NAME}/cortx-test"
		}
    }
    stages {
		stage('CODE_CHECKOUT') {
			steps{
			    cleanWs()
			    checkout([$class: 'GitSCM', branches: [[name: "*/${Git_Branch}"]], doGenerateSubmoduleConfigurations: false, extensions: [], submoduleCfg: [], userRemoteConfigs: [[credentialsId: 'rel_sanity_github_auto', url: "${Git_Repo}"]]])
			}
		}
		stage('ENV_SETUP') {
			steps{
			    echo "${WORKSPACE}"
			    writeFile file: 'prov_config.ini', text: params.Provisioner_Config
			    echo "Copy Provisioner Config file"
			    sh label: '', script: '''
			    if [ -s prov_config.ini ]
			    then echo 'prov_config.ini created with entered details'
			    else
			    echo 'No details entered, Deployment will be done with default configurations'
			    fi
			    '''
			    sh label: '',script: '''
			    sh scripts/jenkins_job/virt_env_setup.sh . venv
                source venv/bin/activate
                python --version
                deactivate
                '''
			    script {
			    withCredentials([file(credentialsId: 'qa_secrets_json_new', variable: 'secrets_json_path')]) {
                sh "cp /$secrets_json_path $WORKSPACE/secrets.json"
				        }
				      }
            }
		}
        stage('DEPLOYMENT')
        {
            steps{
            sh label: '', script: ''' source venv/bin/activate
export Build="${Cortx_Build}"
export Build_Branch="${Cortx_Build_Branch}"
export MGMT_VIP="${MGMT_VIP}"
export HOST_PASS="${HOST_PASS}"
pytest tests/prov/test_prov_three_node.py::TestProvThreeNode::test_deployment_three_node_vm --local True --target "${Target_Node}"
deactivate
'''
            }
        }
		stage('CSM_BOARDING') {
			steps{
			    sh label: '', script: '''source venv/bin/activate
export ADMIN_USR="${ADMIN_USR}"
export ADMIN_PWD="${ADMIN_PWD}"
export MGMT_VIP="${HOSTNAME}"
python -m unittest scripts.jenkins_job.cortx_pre_onboarding.CSMBoarding.test_preboarding
#python -m unittest scripts.jenkins_job.cortx_pre_onboarding.CSMBoarding.test_onboarding
deactivate
'''
			}
		}
		stage('CLIENT_CONFIG') {
			steps{
			    sh label: '', script: '''source venv/bin/activate
python3.7 scripts/jenkins_job/deploy_3_node_vm_ec/client_setup.py "${Node1_Hostname}" "${Node2_Hostname}" "${Node3_Hostname}" --node_count 3 --password "${HOST_PASS}" --mgmt_vip "${MGMT_VIP}"
set +x
echo 'Creating s3 account and configuring awscli on client'
pytest scripts/jenkins_job/aws_configure.py --local True --target ${Target_Node}
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
				emailext body: '${SCRIPT, template="REL_QA_SANITY_CUS_EMAIL_2.template"}', subject: '$PROJECT_NAME on Build # $CORTX_BUILD - $BUILD_STATUS!', to: 'priyanka.borawake@seagate.com'
			}
		}
	}
}
