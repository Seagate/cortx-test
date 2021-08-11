pipeline {
	agent {
        node {
			label "${Client_Node}"
 			customWorkspace "/root/workspace/${JOB_BASE_NAME}/cortx-test"
		}
    }
    stages {
		stage('CODE_CHECKOUT') {
			steps {
			    cleanWs()
			    checkout([$class: 'GitSCM', branches: [[name: "*/${Git_Branch}"]], doGenerateSubmoduleConfigurations: false, extensions: [], submoduleCfg: [], userRemoteConfigs: [[credentialsId: 'rel_sanity_github_auto', url: "${Git_Repo}"]]])
			    withCredentials([file(credentialsId: 'qa_secrets_json_new', variable: 'secrets_json_path')]) {
                sh "cp /$secrets_json_path $WORKSPACE/secrets.json"
		        }
		    }
		}
		stage('ENV_SETUP') {
			steps {
			    echo "${WORKSPACE}"
     			echo "Skip_Deployment ${params.Skip_Deployment}"
     			echo "Skip_Preboarding ${params.Skip_Preboarding}"
    		    echo "Skip_Onboarding ${params.Skip_Onboarding}"
    		    echo "Skip_S3_Configuration ${params.Skip_S3_Configuration}"

			    writeFile file: 'prov_config.ini', text: params.Provisioner_Config
			    sh label: '', script: '''
			    if [ -s prov_config.ini ]
			    then echo 'prov_config.ini created with entered details'
			    else
			    echo 'No details entered, Deployment will be done with default configurations'
			    rm -f prov_config.ini
			    fi

			    sh scripts/jenkins_job/virt_env_setup.sh . venv
                source venv/bin/activate
                python --version

                deactivate
                '''
            }
        }
        stage('DEPLOYMENT') {
			when { expression { !params.Skip_Deployment } }
            steps {
            sh label: '', script: ''' source venv/bin/activate
export Build=${Cortx_Build}
export Build_Branch=${Cortx_Build_Branch}
pytest tests/prov/test_prov_three_node.py::TestProvThreeNode::test_deployment_three_node_vm --local True --target "${Target_Node}"
deactivate
'''
            }
        }
        stage('CSM_PREBOARDING') {
			when { expression { !params.Skip_Preboarding } }
			steps {
			    sh label: '', script: '''source venv/bin/activate
python -m unittest scripts.jenkins_job.cortx_pre_onboarding.CSMBoarding.test_preboarding
deactivate
'''
			}
		}
		stage('CSM_ONBOARDING') {
			when { expression { !params.Skip_Onboarding  } }
			steps {
			    sh label: '', script: '''source venv/bin/activate
python -m unittest scripts.jenkins_job.cortx_pre_onboarding.CSMBoarding.test_onboarding
deactivate
'''
			}
		}
		stage('CLIENT_CONFIG') {
		    when { expression { !params.Skip_S3_Configuration } }
			steps {
			    sh label: '', script: '''source venv/bin/activate
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
