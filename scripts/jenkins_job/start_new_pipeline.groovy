pipeline {
	agent {
        node {
			label 'ssc-vm-4830'
 			customWorkspace "/root/workspace/${JOB_BASE_NAME}"
		}
    }
    environment {
		Target_Node = 'single-node-' + "${"${HOSTNAME}".split("\\.")[0]}"
		Build_Branch = "${"${CORTX_BUILD}".split("\\#")[0]}"
		Build_VER = "${"${CORTX_BUILD}".split("\\#")[1]}"
		Sequential_Execution = 'true'
		Original_TP = 'TEST-22970'
		Sanity_TE = 'TEST-24046'
		Setup_Type = 'default'
		Platform_Type = 'VM'
		Nodes_In_Target = 1
		Server_Type = 'SMC'
		Enclosure_Type = '5U84'
    }
    stages {
		stage('CODE_CHECKOUT') {
			steps{
				cleanWs()
			    checkout([$class: 'GitSCM', branches: [[name: '*/EOS-21228-integrate-test-runner-in-sanity']], doGenerateSubmoduleConfigurations: false, extensions: [], submoduleCfg: [], userRemoteConfigs: [[credentialsId: 'ef9a4dc6-3f22-42bf-bafe-a39ba5042683', url: 'https://github.com/NiteshMahajan/cortx-test.git']]])
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
python -m unittest scripts.jenkins_job.cortx_pre_onboarding.CSMBoarding.test_preboarding
python -m unittest scripts.jenkins_job.cortx_pre_onboarding.CSMBoarding.test_onboarding
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
				withCredentials([usernamePassword(credentialsId: 'ae26299e-5fc1-4fd7-86aa-6edd535d5b4f', passwordVariable: 'JIRA_PASSWORD', usernameVariable: 'JIRA_ID')]) {
					sh label: '', script: '''source venv/bin/activate
set +x
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
			python3 -u testrunner.py -te=$te_id -tp=$tp_id -tg=${Target_Node} -b=${Build_VER} -t=${Build_Branch} --force_serial_run ${Sequential_Execution} --xml_report sanity-results.xml
		fi
done < $INPUT
IFS=$OLDIFS
deactivate
'''				}
			}
		}
		stage('REGRESSION_TEST_EXECUTION') {
			steps{
				withCredentials([usernamePassword(credentialsId: 'ae26299e-5fc1-4fd7-86aa-6edd535d5b4f', passwordVariable: 'JIRA_PASSWORD', usernameVariable: 'JIRA_ID')]) {
					sh label: '', script: '''source venv/bin/activate
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
			python3 -u testrunner.py -te=$te_id -tp=$tp_id -tg=${Target_Node} -b=${Build_VER} -t=${Build_Branch} --force_serial_run ${Sequential_Execution} --xml_report regression-results.xml
		fi
done < $INPUT
IFS=$OLDIFS
deactivate
'''
				}
			}
		}
    }
	post {
		always {
			catchError(stageResult: 'FAILURE') {
			    junit allowEmptyResults: true, testResults: 'log/*results.xml'
				emailext body: '${SCRIPT, template="REL_QA_SANITY_CUS_EMAIL_2.template"}', subject: '$PROJECT_NAME on Build # $CORTX_BUILD - $BUILD_STATUS!', to: 'nitesh.mahajan@seagate.com'
			}
		}
	}
}
