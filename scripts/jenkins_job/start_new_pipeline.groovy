pipeline {
	agent {
        node {
			label 'qa-re-sanity-nodes'
 			customWorkspace "/root/workspace/${JOB_BASE_NAME}"
		}
    }
    environment {
		Target_Node = 'single-node-' + "${"${HOSTNAME}".split("\\.")[0]}"
		Build_Branch = "${"${CORTX_BUILD}".split("\\#")[0]}"
		Build_VER = "${"${CORTX_BUILD}".split("\\#")[1]}"
		Sequential_Execution = true
		Original_TP = 'TEST-22970'
		Sanity_TE = 'TEST-24046'
		Setup_Type = 'default'
		Platform_Type = 'VM'
		Nodes_In_Target = 1
		Server_Type = 'SMC'
		Enclosure_Type = '5U84'
		DB_Update = false
		Current_TP = "None"
		Sanity_Failed = true
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
		stage('COPY_TP_TE') {
			steps{
				withCredentials([usernamePassword(credentialsId: 'ae26299e-5fc1-4fd7-86aa-6edd535d5b4f', passwordVariable: 'JIRA_PASSWORD', usernameVariable: 'JIRA_ID')]) {
					sh label: '', script: '''source venv/bin/activate
python3.7 -u tools/clone_test_plan/clone_test_plan.py -tp=${Original_TP} -b=${Build_VER} -br=${Build_Branch} -s=${Setup_Type} -n=${Nodes_In_Target} -sr=${Server_Type} -e=${Enclosure_Type} -p=${Platform_Type}
deactivate
'''
}
			}
		}
		stage('SANITY_TEST_EXECUTION') {
			steps{
				script {
			        env.Sanity_Failed = true
			        env.Health = 'OK'

				withCredentials([usernamePassword(credentialsId: 'ae26299e-5fc1-4fd7-86aa-6edd535d5b4f', passwordVariable: 'JIRA_PASSWORD', usernameVariable: 'JIRA_ID')]) {
					status = sh (label: '', returnStatus: true, script: '''#!/bin/sh
source venv/bin/activate
set +x
echo 'Creating s3 account and configuring awscli on client'
pytest scripts/jenkins_job/aws_configure.py::test_create_acc_aws_conf --local True --target ${Target_Node}
set -e
INPUT=cloned_tp_info.csv
OLDIFS=$IFS
IFS=','
[ ! -f $INPUT ] && { echo "$INPUT file not found"; exit 99; }
while read tp_id te_id old_te
do
    old_te=$(echo $old_te | sed -e 's/\r//g')
    if [ "${old_te}" == "${Sanity_TE}" ]
		then
			echo "Running Sanity Tests"
			echo "tp_id : $tp_id"
			echo "te_id : $te_id"
			echo "old_te : $old_te"
			(set -x; python3 -u testrunner.py -te=$te_id -tp=$tp_id -tg=${Target_Node} -b=${Build_VER} -t=${Build_Branch} --force_serial_run ${Sequential_Execution} -d=${DB_Update} --xml_report True)
		fi
done < $INPUT
IFS=$OLDIFS
deactivate
''' )
				    }
				    if ( status != 0 ) {
                        currentBuild.result = 'FAILURE'
                        env.Health = 'Not OK'
                        error('Aborted Sanity due to bad health of deployment')
                    }
                    if ( fileExists('log/latest/failed_tests.log') ) {
                        def failures = readFile 'log/latest/failed_tests.log'
                        def lines = failures.readLines()
                        if (lines) {
                            echo "Sanity Test Failed"
                            currentBuild.result = 'FAILURE'
                            error('Skipping Regression as Sanity Test Failed')
                        }
                    }
				}
			}
		}
		stage('REGRESSION_TEST_EXECUTION') {
			steps {
				script {
			        env.Sanity_Failed = false
			        env.Health = 'OK'

				withCredentials([usernamePassword(credentialsId: 'ae26299e-5fc1-4fd7-86aa-6edd535d5b4f', passwordVariable: 'JIRA_PASSWORD', usernameVariable: 'JIRA_ID')]) {
					status = sh (label: '', returnStatus: true, script: '''#!/bin/sh
source venv/bin/activate
set +x
INPUT=cloned_tp_info.csv
OLDIFS=$IFS
IFS=','
[ ! -f $INPUT ] && { echo "$INPUT file not found"; exit 99; }
while read tp_id te_id old_te
do
    old_te=$(echo $old_te | sed -e 's/\r//g')
    if [ "${old_te}" != "${Sanity_TE}" ]
		then
			echo "Running Regression Tests"
			echo "tp_id : $tp_id"
			echo "te_id : $te_id"
			echo "old_te : $old_te"
			(set -x; python3 -u testrunner.py -te=$te_id -tp=$tp_id -tg=${Target_Node} -b=${Build_VER} -t=${Build_Branch} --force_serial_run ${Sequential_Execution} -d=${DB_Update} --xml_report True)
		fi
done < $INPUT
IFS=$OLDIFS
deactivate
''' )
				    }
				    if ( status != 0 ) {
                        currentBuild.result = 'FAILURE'
                        env.Health = 'Not OK'
                        error('Aborted Regression due to bad health of deployment')
                    }
				}
			}
		}
    }
	post {
		always {
		    script {
        		  if ( fileExists('cloned_tp_info.csv') ) {
            		  def records = readCSV file: 'cloned_tp_info.csv'
            		  env.Current_TP = records[0][0]
        		  }
		     }
			catchError(stageResult: 'FAILURE') {
			    archiveArtifacts allowEmptyArchive: true, artifacts: 'log/*report.xml, log/*report.html, *.png', followSymlinks: false
			    junit allowEmptyResults: true, testResults: 'log/*report.xml'
				emailext body: '${SCRIPT, template="REL_QA_SANITY_CUS_EMAIL_3.template"}', subject: '$PROJECT_NAME on Build # $CORTX_BUILD - $BUILD_STATUS!', to: 'cortx.automation@seagate.com'
			}
		}
	}
}
