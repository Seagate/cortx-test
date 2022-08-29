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
		    if [ -e "log/latest/failed_tests.log" ] ; then echo "Exists\n" >> stage_fail.log ; fi
		fi
done < $INPUT
IFS=$OLDIFS
deactivate
''' )
				    }
				    if ( fileExists('stage_fail.log') || fileExists('log/latest/failed_tests.log') ) {
                        echo "Regression Test Failed"
                        env.Regression_Failed = true
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
python3 scripts/jenkins_job/get_tests_count.py -ji=${JIRA_ID} -jp=${JIRA_PASSWORD}
python3 scripts/jenkins_job/job_duration.py -bl=$BUILD_URL
deactivate
'''
}
                  if ( fileExists('te_tests_count.csv')) {
                      def testcount = readCSV file: 'te_tests_count.csv'
                      testcount.with {
                          env.santotalcount = testcount[0][1]
                          env.sanpasscount = testcount[0][2]
                          env.sanfailcount = testcount[0][3]
                          env.sanskipcount = testcount[0][4]
                          env.santodocount = testcount[0][5]
                          env.sanabortcount = testcount[0][6]
                          env.itotalcount = testcount[1][1]
                          env.ipasscount = testcount[1][2]
                          env.ifailcount = testcount[1][3]
                          env.iskipcount = testcount[1][4]
                          env.itodocount = testcount[1][5]
                          env.iabortcount = testcount[1][6]
                          env.ftotalcount = testcount[2][1]
                          env.fpasscount = testcount[2][2]
                          env.ffailcount = testcount[2][3]
                          env.fskipcount = testcount[2][4]
                          env.ftodocount = testcount[2][5]
                          env.fabortcount = testcount[2][6]
                          env.rtotalcount = testcount[3][1]
                          env.rpasscount = testcount[3][2]
                          env.rfailcount = testcount[3][3]
                          env.rskipcount = testcount[3][4]
                          env.rtodocount = testcount[3][5]
                          env.rabortcount = testcount[3][6]
                          env.totalcount = testcount[4][1]
                          env.passcount = testcount[4][2]
                          env.failcount = testcount[4][3]
                          env.skipcount = testcount[4][4]
                          env.todocount = testcount[4][5]
                          env.abortcount = testcount[4][6]
                      }
 }
                  if ( fileExists('stages_duration.csv')) {
                      def duration = readCSV file: 'stages_duration.csv'
                      duration.with {
                          env.sanitytime = duration[0][1]
                          env.regrtime = duration[1][1]
                          env.iotime = duration[2][1]
                          env.fdtime = duration[3][1]
                          env.totaltime = duration[4][1]
                      }
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
			    archiveArtifacts allowEmptyArchive: true, artifacts: 'log/*report.xml, log/*report.html, support_bundle/*.tgz, crash_files/*.gz', followSymlinks: false
				emailext body: '${SCRIPT, template="REL_QA_SANITY_CUS_EMAIL_5_v2.template"}', subject: '$PROJECT_NAME on Build # $CORTX_IMAGE - $BUILD_STATUS!', to: 'sonal.kalbende@seagate.com,akshay.s.mankar@seagate.com'
			}
		}
	}
}
