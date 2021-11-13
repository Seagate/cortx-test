pipeline {
	agent {
        node {
			label 'qa-re-sanity-nodes'
 			customWorkspace "/root/workspace/${JOB_BASE_NAME}"
		}
    }
    environment {
		Target_Node = 'multi-node-' + "${"${M_NODE}".split("\\.")[0]}"
		Build_Branch = "${"${CORTX_BUILD}".split("\\#")[0]}"
		Build_VER = "${"${CORTX_BUILD}".split("\\#")[1]}"
		Sequential_Execution = true
		Original_TP = 'TEST-31310'
		Sanity_TE = 'TEST-31311'
		Setup_Type = 'default'
		Platform_Type = 'VM'
		Nodes_In_Target = "${NUM_NODES}"
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
			    checkout([$class: 'GitSCM', branches: [[name: '*/lc_dev']], doGenerateSubmoduleConfigurations: false, extensions: [], submoduleCfg: [], userRemoteConfigs: [[credentialsId: 'rel_sanity_github_auto', url: 'https://github.com/Seagate/cortx-test.git']]])
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
sh scripts/cicd_k8s/lb_haproxy.sh
python3.7 scripts/cicd_k8s/client_multinode_conf.py --master_node "${M_NODE}" --password "${HOST_PASS}" --mgmt_vip "${MGMT_VIP}" --node_count "${NUM_NODES}"
deactivate
'''
			}
	    }
		stage('COPY_TP_TE') {
			steps{
				withCredentials([usernamePassword(credentialsId: 'ea9a9c11-7f66-43c5-8a32-5311b0cb9cf4', passwordVariable: 'JIRA_PASSWORD', usernameVariable: 'JIRA_ID')]) {
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

				withCredentials([usernamePassword(credentialsId: 'ea9a9c11-7f66-43c5-8a32-5311b0cb9cf4', passwordVariable: 'JIRA_PASSWORD', usernameVariable: 'JIRA_ID')]) {
					status = sh (label: '', returnStatus: true, script: '''#!/bin/sh
source venv/bin/activate
set +x
echo 'Creating s3 account and configuring awscli on client'
pytest scripts/jenkins_job/aws_configure.py::test_create_acc_aws_conf --local True --target ${Target_Node} --health_check False
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
			(set -x; python3 -u testrunner.py -te=$te_id -tp=$tp_id -tg=${Target_Node} -b=${Build_VER} -t=${Build_Branch} --force_serial_run ${Sequential_Execution} -d=${DB_Update} --xml_report True --health_check=False)
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

				withCredentials([usernamePassword(credentialsId: 'ea9a9c11-7f66-43c5-8a32-5311b0cb9cf4', passwordVariable: 'JIRA_PASSWORD', usernameVariable: 'JIRA_ID')]) {
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
			(set -x; python3 -u testrunner.py -te=$te_id -tp=$tp_id -tg=${Target_Node} -b=${Build_VER} -t=${Build_Branch} --force_serial_run ${Sequential_Execution} -d=${DB_Update} --xml_report True --health_check=False)
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
        		  /* if ( currentBuild.currentResult == "FAILURE" || currentBuild.currentResult == "UNSTABLE" ) {
        		  try {
        		      sh label: '', script: '''source venv/bin/activate
export MGMT_VIP="${HOSTNAME}"
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
		     } */
			catchError(stageResult: 'FAILURE') {
			    archiveArtifacts allowEmptyArchive: true, artifacts: 'log/*report.xml, log/*report.html, support_bundle/*.tar, crash_files/*.gz', followSymlinks: false
				emailext body: '${SCRIPT, template="REL_QA_SANITY_CUS_EMAIL_3.template"}', subject: '$PROJECT_NAME on Build # $CORTX_BUILD - $BUILD_STATUS!', to: 'sonal.kalbende@seagate.com'
			}
		}
	}
}
}