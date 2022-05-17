pipeline {
	agent {
        node {
			label 'qa-re-sanity-nodes'
 			customWorkspace "/root/workspace/${JOB_BASE_NAME}"
		}
    }
    environment {
		Target_Node = 'multi-node-' + "${"${M_NODE}".split("\\.")[0]}"
		Build_Branch = "${"${CORTX_IMAGE}".split(":")[0]}"
		Build_VER = "${"${CORTX_IMAGE}".split(":")[1]}"
		Sequential_Execution = true
		Original_TP = 'TEST-37457'
		Sanity_TE = 'TEST-37458'
		Data_Path_TE = 'TEST-39283'
		Failure_TE = 'TEST-40061'
		Setup_Type = 'NightlySanity'
		Platform_Type = 'VM'
		Nodes_In_Target = "${NUM_NODES}"
		Server_Type = 'SMC'
		Enclosure_Type = '5U84'
		DB_Update = false
		Current_TP = "None"
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
		stage('COPY_TP_TE') {
			steps{
				withCredentials([usernamePassword(credentialsId: 'nightly_sanity', passwordVariable: 'JIRA_PASSWORD', usernameVariable: 'JIRA_ID')]) {
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
			        env.Sanity_Failed = false
			        env.Health = 'OK'

				withCredentials([usernamePassword(credentialsId: 'nightly_sanity', passwordVariable: 'JIRA_PASSWORD', usernameVariable: 'JIRA_ID')]) {
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
			(set -x; python3 -u testrunner.py -te=$te_id -tp=$tp_id -tg=${Target_Node} -b=${Build_VER} -t=${Build_Branch} --force_serial_run ${Sequential_Execution} -d=${DB_Update} --xml_report True --validate_certs False)
		fi
done < $INPUT
IFS=$OLDIFS
deactivate
'''	)
				    }
				    if ( fileExists('log/latest/failed_tests.log') ) {
                        def failures = readFile 'log/latest/failed_tests.log'
                        def lines = failures.readLines()
                        if (lines) {
                            echo "Sanity Test Failed"
                            env.Sanity_Failed = true
                            currentBuild.result = 'FAILURE'
                        }
                    }
				    if ( status != 0 ) {
                        currentBuild.result = 'FAILURE'
                        env.Health = 'Not OK'
                        env.Sanity_Failed = true
                        error('Aborted Sanity due to bad health of deployment')
                    }
				}
			}
		}
		stage('REGRESSION_TEST_EXECUTION') {
			steps {
				script {
			        env.Health = 'OK'
                    env.Regression_Failed = false
				withCredentials([usernamePassword(credentialsId: 'nightly_sanity', passwordVariable: 'JIRA_PASSWORD', usernameVariable: 'JIRA_ID')]) {
					status = sh (label: '', returnStatus: true, script: '''#!/bin/sh
source venv/bin/activate
set +x
set -e
INPUT=cloned_tp_info.csv
OLDIFS=$IFS
IFS=','
[ ! -f $INPUT ] && { echo "$INPUT file not found"; exit 99; }
while read tp_id te_id old_te
do
    old_te=$(echo $old_te | sed -e 's/\r//g')
    if [ "${old_te}" != "${Sanity_TE}" ] && [ "${old_te}" != "${Data_Path_TE}" ] && [ "${old_te}" != "${Failure_TE}" ]
		then
			echo "Running Regression Tests"
			echo "tp_id : $tp_id"
			echo "te_id : $te_id"
			echo "old_te : $old_te"
			(set -x; python3 -u testrunner.py -te=$te_id -tp=$tp_id -tg=${Target_Node} -b=${Build_VER} -t=${Build_Branch} --force_serial_run ${Sequential_Execution} -d=${DB_Update} --xml_report True --validate_certs False)
		fi
done < $INPUT
IFS=$OLDIFS
deactivate
''' )
				    }
				    if ( fileExists('log/latest/failed_tests.log') ) {
                        def failures = readFile 'log/latest/failed_tests.log'
                        def rlines = failures.readLines()
                        if (rlines) {
                            echo "Regression Test Failed"
                            env.Regression_Failed = true
                        }
                    }
                    if ( status != 0 ) {
                        currentBuild.result = 'FAILURE'
                        env.Health = 'Not OK'
                        env.Regression_Failed = true
                        error('Aborted Regression due to bad health of deployment')
                    }
				}
			}
		}
		stage('IO_PATH_TEST_EXECUTION') {
			steps {
				script {
			        env.Health = 'OK'
                    env.Io_Path_Failed = false
				withCredentials([usernamePassword(credentialsId: 'nightly_sanity', passwordVariable: 'JIRA_PASSWORD', usernameVariable: 'JIRA_ID')]) {
					status = sh (label: '', returnStatus: true, script: '''#!/bin/sh
source venv/bin/activate
set +x
set -e
INPUT=cloned_tp_info.csv
OLDIFS=$IFS
IFS=','
[ ! -f $INPUT ] && { echo "$INPUT file not found"; exit 99; }
while read tp_id te_id old_te
do
    old_te=$(echo $old_te | sed -e 's/\r//g')
    if [ "${old_te}" == "${Data_Path_TE}" ]
		then
			echo "Running IO Path Tests"
			echo "tp_id : $tp_id"
			echo "te_id : $te_id"
			echo "old_te : $old_te"
			(set -x; python3 -u testrunner.py -te=$te_id -tp=$tp_id -tg=${Target_Node} -b=${Build_VER} -t=${Build_Branch} --force_serial_run ${Sequential_Execution} -d=${DB_Update} --xml_report True --validate_certs False)
		fi
done < $INPUT
IFS=$OLDIFS
deactivate
''' )
				    }
				    if ( fileExists('log/latest/failed_tests.log') ) {
                        def failures = readFile 'log/latest/failed_tests.log'
                        def ilines = failures.readLines()
                        if (ilines) {
                            echo "IO_PATH_TEST Test Failed"
                            env.Io_Path_Failed = true
                        }
                    }
				    if ( status != 0 ) {
                        currentBuild.result = 'FAILURE'
                        env.Health = 'Not OK'
                        env.Io_Path_Failed = true
                        error('Aborted IO Path due to bad health of deployment')
                    }
				}
			}
		}
		stage('FAILURE_DOMAIN_TEST_EXECUTION') {
			steps {
				script {
			        env.Health = 'OK'
                    env.Failure_Domain_Failed = false
				withCredentials([usernamePassword(credentialsId: 'nightly_sanity', passwordVariable: 'JIRA_PASSWORD', usernameVariable: 'JIRA_ID')]) {
					status = sh (label: '', returnStatus: true, script: '''#!/bin/sh
source venv/bin/activate
set +x
set -e
INPUT=cloned_tp_info.csv
OLDIFS=$IFS
IFS=','
[ ! -f $INPUT ] && { echo "$INPUT file not found"; exit 99; }
while read tp_id te_id old_te
do
    old_te=$(echo $old_te | sed -e 's/\r//g')
    if [ "${old_te}" == "${Failure_TE}" ]
		then
			echo "Running Failure Domain Tests"
			echo "tp_id : $tp_id"
			echo "te_id : $te_id"
			echo "old_te : $old_te"
			(set -x; python3 -u testrunner.py -te=$te_id -tp=$tp_id -tg=${Target_Node} -b=${Build_VER} -t=${Build_Branch} --force_serial_run ${Sequential_Execution} -d=${DB_Update} --xml_report True --validate_certs False)
		fi
done < $INPUT
IFS=$OLDIFS
deactivate
''' )
				    }
				    if ( fileExists('log/latest/failed_tests.log') ) {
                        def failures = readFile 'log/latest/failed_tests.log'
                        def flines = failures.readLines()
                        if (flines) {
                            echo "FAILURE DOMAIN Test Failed"
                            env.Failure_Domain_Failed = true
                        }
                    }
				    if ( status != 0 ) {
                        currentBuild.result = 'FAILURE'
                        env.Health = 'Not OK'
                        env.Failure_Domain_Failed = true
                        error('Aborted Failure Domain Path due to bad health of deployment')
                    }
				}
			}
		}
    }
	post {
		always {
		    junit allowEmptyResults: true, testResults: 'log/*report.xml'
		    script {
		          env.Regression_overall_failed = false
		          if ( env.Regression_Failed != false || env.Io_Path_Failed != false || env.Failure_Domain_Failed != false ) {
                     env.Regression_overall_failed = true
                  }
        		  if ( fileExists('cloned_tp_info.csv') ) {
            		  def records = readCSV file: 'cloned_tp_info.csv'
            		  env.Current_TP = records[0][0]
            		  env.new_TP = records[0][0]
        		  }
        		   withCredentials([usernamePassword(credentialsId: 'nightly_sanity', passwordVariable: 'JIRA_PASSWORD', usernameVariable: 'JIRA_ID')]) {
					sh label: '', script: '''source venv/bin/activate
export PYTHONPATH=$WORKSPACE:$PYTHONPATH
python3 scripts/jenkins_job/get_tests_count.py -tp=${new_TP} -ji=${JIRA_ID} -jp=${JIRA_PASSWORD}
deactivate
'''
}
                  if ( fileExists('total_count.csv')) {
                      def testcount = readCSV file: 'total_count.csv'
                      testcount.with {
                          env.totalcount = testcount[0][0]
                          env.passcount = testcount[0][1]
                          env.failcount = testcount[0][2]
                          env.skipcount = testcount[0][3]
                          env.todocount = testcount[0][4]
                          env.abortcount = testcount[0][5]
                      }
                      echo "Total : ${totalcount}"
                      echo "Pass : ${passcount}"
                      echo "Fail : ${failcount}"
                      echo "Skip : ${skipcount}"
                      echo "Todo : ${todocount}"
                      echo "Aborted : ${abortcount}"
 }
        		  if ( currentBuild.currentResult == "FAILURE" || currentBuild.currentResult == "UNSTABLE" ) {
        		  try {
        		      sh label: '', script: '''source venv/bin/activate
pytest scripts/jenkins_job/aws_configure.py::test_collect_support_bundle_single_cmd --local True --health_check False --target ${Target_Node}
deactivate
'''
} catch (err) {
    echo "Caught error in SB: ${err}"
}
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
				emailext body: '${SCRIPT, template="REL_QA_SANITY_CUS_EMAIL_5_v2.template"}', subject: '$PROJECT_NAME on Build # $CORTX_IMAGE - $BUILD_STATUS!', to: 'sonal.kalbende@seagate.com'
			}
		}
	}
}
