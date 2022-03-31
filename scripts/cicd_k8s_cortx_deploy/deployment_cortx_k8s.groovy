pipeline {
	agent {
        node {
			label "${CLIENT_NODE}"
 			customWorkspace "/root/${JOB_BASE_NAME}/cortx-test"
		}
    }
    stages {
		stage('CODE_CHECKOUT') {
			steps {
			    cleanWs()
			    checkout([$class: 'GitSCM', branches: [[name: "*/${GIT_BRANCH}"]], doGenerateSubmoduleConfigurations: false, extensions: [], submoduleCfg: [], userRemoteConfigs: [[credentialsId: 'rel_sanity_github_auto', url: "${GIT_REPO}"]]])
			    withCredentials([file(credentialsId: 'qa_secrets_json_new', variable: 'secrets_json_path')]) {
                sh "cp /$secrets_json_path $WORKSPACE/secrets.json"
		        }
		    }
		}
		stage('ENV_SETUP') {
			steps {
			    echo "${WORKSPACE}"
			    echo "BUILD : ${BUILD}"
			    echo "Service Release : ${GIT_SCRIPT_TAG}"
			    echo "TP : ${TEST_PLAN_NUMBER}"
			    sh label: '', script: '''
                    yum install -y nfs-utils
                    yum install -y s3cmd
                    yum install -y s3fs-fuse
                    sh scripts/jenkins_job/virt_env_setup.sh . venv
                    source venv/bin/activate
                    python --version
                    deactivate
                '''
            }
        }
        stage('CREATE_SETUP_ENTRY') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'cortxadmin', passwordVariable: 'ADMIN_PASSWORD', usernameVariable: 'ADMIN_USER')]) {
                sh label: '', script: '''source venv/bin/activate
                    export PYTHONPATH="$PWD"
                    export TEST_PLAN_NUMBER=${TEST_PLAN_NUMBER}
                    echo ${TEST_PLAN_NUMBER}
                    SETUP_FILE="cicd_setup_name.txt"
                    ALL_SETUP_ENTRY="all_setup_entry.txt"
                    for te in $(echo ${TEST_EXECUTION_NUMBER})
                    do
					    echo $te
                        export TEST_EXECUTION_NUMBER=$te
                        rm -rf $SETUP_FILE
                        python scripts/cicd_k8s_cortx_deploy/create_db_entry.py
                        if [ -f "$SETUP_FILE" ]
                        then
                            echo "****DB entry successful****"
                            target_name=`cat $SETUP_FILE`
                            echo $target_name >> $ALL_SETUP_ENTRY
                        fi
                    done
                    deactivate
                    '''
                }
            }
        }
        stage('TEST_EXECUTION') {
            steps {
                script {
                    try {
sh (label: '', script: '''source venv/bin/activate
TEST_TYPES=''
TODO_TYPE='TODO'
FAILED_TYPE='FAIL'
BLOCKED_TYPE='BLOCKED'
ABORTED_TYPE='ABORTED'
EXECUTING_TYPE='EXECUTING'
if ${All_Tests}; then
    TEST_TYPES="ALL"
else
    if ${Todo_Tests}; then
	    TEST_TYPES="${TEST_TYPES} ${TODO_TYPE}"
	fi
    if ${Failed_Tests}; then
        TEST_TYPES="${TEST_TYPES} ${FAILED_TYPE}"
    fi
    if ${Blocked_Tests}; then
	    TEST_TYPES="${TEST_TYPES} ${BLOCKED_TYPE}"
    fi
    if ${Aborted_Tests}; then
        TEST_TYPES="${TEST_TYPES} ${ABORTED_TYPE}"
    fi
    if ${Executing_Tests}; then
        TEST_TYPES="${TEST_TYPES} ${EXECUTING_TYPE}"
    fi
fi
echo $TEST_TYPES
export PYTHONHTTPSVERIFY='0'
ALL_SETUP_ENTRY="all_setup_entry.txt"
cat $ALL_SETUP_ENTRY
while IFS=' ' read -r target te
    do
		echo "$target"
		echo "$te"
		python3 -u testrunner.py -te=$te -tp=${TEST_PLAN_NUMBER} -tg=$target -b=${BUILD} -t='stable' -d='False' -hc='True' -s='True' -c='True' -p='0' --force_serial_run 'True' --data_integrity_chk='False' -tt $TEST_TYPES --validate_certs False
	done <$ALL_SETUP_ENTRY
export PYTHONPATH="$PWD"
status=`python3 scripts/cicd_k8s_cortx_deploy/result.py`
RESULT="cat test_result.txt"
echo $RESULT
export REPORT=$RESULT
deactivate
''')
               }
               catch (err) {
                   currentBuild.result = "FAILURE"
sh (label: '', script: '''source venv/bin/activate
var_true="true"
if [ "${collect_support_bundle}" = "$var_true" ]; then
    echo "Collect support bundle"
fi
deactivate
''')
               }
               env.TestPlan = "${TEST_PLAN_NUMBER}"
               env.ServicesVersion = "${GIT_SCRIPT_TAG}"
               if ( fileExists("test_result.txt") ) {
               def file1 = readFile "test_result.txt"
               def lines = file1.readLines()
               env.Report = "$lines"
                   }
               }
           }
       }
   }
	post {
        always {
            emailext body: "${SCRIPT, template="K8s_Cortx_Deployment_test.template"}", subject: "Deployment Test Report on Build # $BUILD - $GIT_SCRIPT_TAG- $BUILD_STATUS!"", to: "${mailRecipients}"
            echo "End of jenkins_job"
        }
    }
}
