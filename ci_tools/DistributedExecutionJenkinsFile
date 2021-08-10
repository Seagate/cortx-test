pipeline {

    agent { label parameters.AGENT }
    environment {
        AWS_ACCESS_KEY_ID     = ''
        AWS_SECRET_ACCESS_KEY = ''
    }

    options {
        timeout(time: 120, unit: 'MINUTES')
        timestamps()

    }

    triggers {

        cron('H 23 * * *')
    }

    parameters {
        string(name: 'TEs', description: 'Space separated TEs', trim: true)
        string(name: 'client', description: 'Setup Client machine', trim: true)
        string(name: 'Branch', defaultValue: 'dev', description: 'Branch name of cortx-test', trim: true)
        string(name: 'TestPlanNumber', defaultValue: 'TEST-18383', description: 'Master Test plan number to clone', trim: true)
        string(name: 'SetupName', description: 'Name of target setup mentioned in database', trim: true)
        text(name: 'DESC', description: 'This job triggers deploy setup and runs Cortx-test TE')
        string(name: 'Nodes_In_Target', defaultValue: '3', description: 'Number of nodes in target: 3 or 3N', trim: true)
        string(name: 'vm_list', defaultValue: '', description: 'List of VMs for 3 Node Setup', trim: true)
        string(name: 'm_vip', defaultValue: '', description: 'Mgmt VIP', trim: true)
        string(name: 'Build', description: 'Build number of target', trim: true)
        string(name: 'Build_Path', description: '3 Node Build Path', trim: true)
        string(name: 'Build_Type', defaultValue: 'stable', description: 'Branch name from which build is cut stable/main', trim: true)
        booleanParam(name: 'DB_Update', description: 'Tick this if you want to push test execution data to database')
        booleanParam(name: 'Sequential_Execution', description: 'Tick this if you want to have sequential execution')
        string(name: 'Process_Cnt_Parallel_Exe', defaultValue: '2', description: 'If Sequential Execution is not selected, then provide number of parallel process to run.', trim: true)
        string(name: 'JIRA_ID', description: 'Jira User ID', trim: true)
        password(name: 'JIRA_PASSWORD', defaultValue: '', description: 'Jira Password of User ID')
        string(name: 'TOKEN', defaultValue: "mk\$4Seagate", description: 'Deployment Token', trim: true)

    }

    stages {
        parallel {
            stage('Checkout cortx-test on client vm') {
                agent { (2)
                    label 'linux'
                }
                when { expression { true } }
                steps {
                    script {
                        step([$class: 'WsCleanup'])
                        dir('cortx-test') {
                            sh "pwd"
                            checkout([$class: 'GitSCM', branches: [[name: "${Branch}"]], doGenerateSubmoduleConfigurations: false, extensions: [[$class: 'AuthorInChangelog'], [$class: 'SubmoduleOption', disableSubmodules: false, parentCredentials: true, recursiveSubmodules: true, reference: '', trackingSubmodules: false]], submoduleCfg: [], userRemoteConfigs: [[credentialsId: 'cortx-admin-github', url: 'https://github.com/Seagate/cortx-test.git']]])
                            sh label: '', script: 'chmod 777 ./ci_tools/client_setup.sh'
                            sh './ci_tools/client_setup.sh'
                        }
                        sh "pwd"
                    }

                }
            }
            stage('Configure AWS') {
                agent { (2)
                    label 'linux'
                }
                steps {
                    dir('cortx-test') {
                        script {
                            def username = "admin"
                            def password = "Seagate@1"
                            def account_name = 'dadmin'
                            def account_email = 'dadmin@seagate.com'
                            def acc_password = 'Seagate@1'
                            sh "python3.7 scripts/s3_tools/create_s3_account.py --mgmt_vip ${m_vip} --username ${username} --password ${password} --account_name ${account_name} --account_email ${account_email} --account_password ${acc_password}"
                            def keys = readFile "${WORKSPACE}/s3acc_secrets"
                            def (access, secret) = keys.tokenize(' ')
                            sh "cd ${WORKSPACE}/cortx-test/scripts/s3_tools/"
                            sh "make clean --makefile=scripts/s3_tools/Makefile"
                            sh "make configure-tools --makefile=scripts/s3_tools/Makefile ACCESS=access SECRET=secret"

                        }
                    }

                }
            }
        }

        stage('Executing Load, API and UI Tests in parallel') {
            parallel {
                stage('Cortx-Text Automation Trigger Drunner') {
                    agent { (2)
                        label 'linux'
                    }
                    steps {
                        script {
                            def name = "${params.TestPlanNumber}"
                            echo "Executing $name"
                        }
                        catchError {
                            sh label: '', script: '''source virenv/bin/activate
                            export PYTHONPATH=$WORKSPACE/cortx-test:$PYTHONPATH
                            cd $WORKSPACE/cortx-test/
                            echo $PYTHONPATH
                            python3.7 setup_switch.py -te ${TEs} -tp ${TestPlanNumber} -b ${Build} -t ${Build_Type} -d ${DB_Update} -pe ${Process_Cnt_Parallel_Exe} -tg ${SetupName}
                            deactivate
                        
                    '''
                        }
                        echo currentBuild.result
                    }
                }
                stage('Cortx-Text Automation Trigger Client1') {
                    agent { (2)
                        label 'linux'
                    }
                    steps {
                        script {
                            def name = "${params.TestPlanNumber}"
                            echo "Executing $name"
                        }
                        catchError {
                            sh label: '', script: '''source virenv/bin/activate
                            export PYTHONPATH=$WORKSPACE/cortx-test:$PYTHONPATH
                            cd $WORKSPACE/cortx-test/
                            echo $PYTHONPATH
                            python3.7 setup_switch.py -te ${TEs} -tp ${TestPlanNumber} -b ${Build} -t ${Build_Type} -d ${DB_Update} -pe ${Process_Cnt_Parallel_Exe} -tg ${SetupName}
                            deactivate
                        
                    '''
                        }
                        echo currentBuild.result
                    }
                }
                stage('Cortx-Text Automation Trigger Client 2') {
                    agent { (2)
                        label 'linux'
                    }
                    steps {
                        script {
                            def name = "${params.TestPlanNumber}"
                            echo "Executing $name"
                        }
                        catchError {
                            sh label: '', script: '''source virenv/bin/activate
                            export PYTHONPATH=$WORKSPACE/cortx-test:$PYTHONPATH
                            cd $WORKSPACE/cortx-test/
                            echo $PYTHONPATH
                            python3.7 setup_switch.py -te ${TEs} -tp ${TestPlanNumber} -b ${Build} -t ${Build_Type} -d ${DB_Update} -pe ${Process_Cnt_Parallel_Exe} -tg ${SetupName}
                            deactivate
                        
                    '''
                        }
                        echo currentBuild.result
                    }
                }
            }
        }

    }

    post {
        always {
            cleanWs()
            dir("${env.WORKSPACE}@tmp") {
                deleteDir()
            }
            dir("${env.WORKSPACE}@script") {
                deleteDir()
            }
            dir("${env.WORKSPACE}@script@tmp") {
                deleteDir()
            }
        }
        success {
            echo "The pipeline ${currentBuild.fullDisplayName} completed successfully."
        }
        failure {
            mail to: 'sarang.sawant@seagate.com',
                    subject: "Failed Pipeline: ${currentBuild.fullDisplayName}",
                    body: "Something is wrong with ${env.BUILD_URL}"
        }

    }
}
