pipeline {
	agent {
        node {
			label 'qa-re-sanity-nodes'
 			customWorkspace "/root/workspace/${JOB_BASE_NAME}"
		}
    }
    environment {
		Target_Node = 'three-node-' + "${"${HOST1}".split("\\.")[0]}"
		Build_Branch = "${"${CORTX_BUILD}".split("\\#")[0]}"
		Build_VER = "${"${CORTX_BUILD}".split("\\#")[1]}"
		Sequential_Execution = true
		Original_TP = 'TEST-24047'
		Sanity_TE = 'TEST-24048'
		Setup_Type = 'default'
		Platform_Type = 'VM'
		Nodes_In_Target = 3
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
			    checkout([$class: 'GitSCM', branches: [[name: '*/cicd_dev']], doGenerateSubmoduleConfigurations: false, extensions: [], submoduleCfg: [], userRemoteConfigs: [[credentialsId: 'rel_sanity_github_auto', url: 'https://github.com/Seagate/cortx-test.git']]])
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
		stage('COPY_TP_TE') {
			steps{
				withCredentials([usernamePassword(credentialsId: 'e8d4e498-3a9b-4565-985a-abd90ac37350', passwordVariable: 'JIRA_PASSWORD', usernameVariable: 'JIRA_ID')]) {
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

				withCredentials([usernamePassword(credentialsId: 'e8d4e498-3a9b-4565-985a-abd90ac37350', passwordVariable: 'JIRA_PASSWORD', usernameVariable: 'JIRA_ID')]) {
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
'''	)
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

				withCredentials([usernamePassword(credentialsId: 'e8d4e498-3a9b-4565-985a-abd90ac37350', passwordVariable: 'JIRA_PASSWORD', usernameVariable: 'JIRA_ID')]) {
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
		    junit allowEmptyResults: true, testResults: 'log/*report.xml'
		    script {
        		  if ( fileExists('cloned_tp_info.csv') ) {
            		  def records = readCSV file: 'cloned_tp_info.csv'
            		  env.Current_TP = records[0][0]
        		  }
        		  if ( currentBuild.currentResult == "FAILURE" || currentBuild.currentResult == "UNSTABLE" ) {
        		  try {
        		      sh label: '', script: '''source venv/bin/activate
export MGMT_VIP="${HOSTNAME}"
pytest scripts/jenkins_job/aws_configure.py::test_collect_support_bundle_single_cmd --local True --health_check False --target ${Target_Node}
deactivate
'''
} catch (err) {
    echo "Caught error in SB: ${err}"
}
                      /* if ( "${CREATE_JIRA_ISSUE}" ) {
                        jiraIssue = createJiraIssue(env.Current_TP)
                        env.jira_issue="https://jts.seagate.com/browse/${jiraIssue}"
                        echo "${jira_issue}"
                      } */
                  }
             try {
             sh label: '', script: '''source venv/bin/activate
pytest scripts/jenkins_job/aws_configure.py::test_collect_crash_files --local True --health_check False --target ${Target_Node}
deactivate
'''
} catch (err) {
    echo "Caught error in crash files collection: ${err}"
}
		     }
			catchError(stageResult: 'FAILURE') {
			    archiveArtifacts allowEmptyArchive: true, artifacts: 'log/*report.xml, log/*report.html, support_bundle/*.tar, crash_files/*.gz', followSymlinks: false
				emailext body: '${SCRIPT, template="REL_QA_SANITY_CUS_EMAIL_3.template"}', subject: '$PROJECT_NAME on Build # $CORTX_BUILD - $BUILD_STATUS!', to: 'sonal.kalbende@seagate.com'
			}
		}
	}
}

def createJiraIssue(String Current_TP) {

    def issue = [
                    fields: [
                        project: [key: 'EOS'],
                        issuetype: [name: 'Bug'],
                        priority: [name: "High"],
                        versions: [[name: "CORTX-R2"]],
                        labels: ["CORTX_QA", "Sanity"],
                        components: [[name: "Automation"]],
                        summary: "${JOB_BASE_NAME} Failed on Build ${CORTX_BUILD}",
                        description: "{panel}${JOB_BASE_NAME} is failed for the build ${CORTX_BUILD}. Please check Jenkins console log and deployment log for more info.\n"+
                                    "\n h4. Test Details \n"+
                                    "|Cortx build|${CORTX_BUILD}|\n"+
                                    "|Jenkins build|[${JOB_BASE_NAME}#${BUILD_NUMBER} |${BUILD_URL}]|\n"+
                                    "|Test Plan |${Current_TP}|\n"+
                                    "|Test Results|[${JOB_BASE_NAME}/${BUILD_NUMBER}/testReport|${BUILD_URL}testReport]|\n"+
                                    "|Client Node|${NODE_NAME}|\n"+
                                    "\n\n"+
                                    "Please find test and support bundle logs at below location: \n"+
                                    "[${JOB_BASE_NAME}/${BUILD_NUMBER}/artifact|${BUILD_URL}artifact] \n {panel}"
                    ]
                ]


    def newIssue = jiraNewIssue issue: issue, failOnError: false, site: 'SEAGATE_QA_JIRA'
    return newIssue.data.key
}
