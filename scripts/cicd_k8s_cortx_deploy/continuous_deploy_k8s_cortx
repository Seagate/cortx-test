pipeline {
	agent {
        node {
			label "${Client_node}"
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
			    echo "BUILD : ${params.BUILD}"
     			echo "Setup k8s cluster ${params.setup_k8s_cluster}"
     			echo "Deploy Cortx Cluster ${params.cortx_cluster_deploy}"
     			echo "Setup Client Config ${params.setup_client_config}"
    		    echo "Run Basic S3 IO ${params.run_basic_s3_io}"
    		    echo "Run S3 bench workload ${params.run_s3bench_workload}"
                echo "Destroy Cortx Setup ${params.destroy_setup}"
                echo "Collect Support Bundle ${params.collect_support_bundle}"
                echo "Raise EOS Jira on failure ${params.raise_jira}"

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

            sh label: '', script: ''' source venv/bin/activate
                SETUP_FILE="cicd_setup_name.txt"
                ALL_SETUP_ENTRY="all_setup_entry.txt"

                for each in $(echo ${WORKER_NODE_CONFIG})
                do
                    export NODES_COUNT=$each
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
                       sh label: '', script: ''' source venv/bin/activate
                        ALL_SETUP_ENTRY="all_setup_entry.txt"
                        cat $ALL_SETUP_ENTRY
                        while IFS= read -r line; do
                           pytest tests/prov/test_cont_deployment.py::TestContDeployment::test_n --local True --target $line
                        done < $ALL_SETUP_ENTRY
                        deactivate
                        '''
                    }
                    catch (err)
                    {
                        currentBuild.result = "FAILURE"
                        sh label: '', script: '''source venv/bin/activate
                        if [ ${collect_support_bundle}=='true' ]; then
                            echo "Collect support bundle"
                        fi
                        if [ ${raise_jira}=='true' ]; then
                            echo "Raise Jira on Failure"
                            python scripts/cicd_k8s_cortx_deploy/create_jira_issue.py
                        fi
                        deactivate
                        '''
                    }
                }
            }
        }
    }
	post {
        always {
            echo "End of jenkins_job"
        }
    }
}
