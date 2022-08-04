#!/usr/bin/env groovy

pipeline {
  agent { label 'executor-v2' }

  options {
    timestamps()
    buildDiscarder(logRotator(numToKeepStr: '30'))
  }

  stages {
    stage('Validate') {
      parallel {
        stage('Changelog') {
          steps { sh './ci/parse-changelog.sh' }
        }
      }
    }
    def ansible_versions = ['4','5']

    stage('Run Open Source tests') {
      parallel {
        stage("Test conjur_variable lookup plugin") {
                  steps {
                                  script {
                                    if ((env.BRANCH_NAME != 'main') || (env.BRANCH_NAME != 'publish*') ) {

                                          for (int i = 0; i < 2; i++)
                                            {
                                              sh 'echo testing only ansible version'
                                              sh """./ci/test.sh -v "${ansible_versions[i]}" -d conjur_variable"""
                                              junit "tests/conjur_variable/junit/*"
                                            }
                                         }
                                        }
                  }
                }
        stage("Test conjur_host_identity role") {
                  steps {

                                  script {
                                    if ((env.BRANCH_NAME != "main") || (env.BRANCH_NAME != 'publish*')){
                                          // def ansible_versions = ['4','5']
                                          for (int j = 0; j < 2; j++)
                                            {
                                              sh 'echo testing only ansible version'
                                               sh """./ci/test.sh -v "${ansible_versions[j]}" -d conjur_host_identity"""
                                               junit "roles/conjur_host_identity/tests/junit/*"
                                            }
                                         }
                                        }

                  }
                }
      }
    }


    stage('Run Open Source tests with latest version') {
      parallel {
        stage("Testing conjur_variable lookup plugin") {
          steps {
            sh './ci/test.sh -v 6 -d conjur_variable'
            junit 'tests/conjur_variable/junit/*'
          }
        }

        stage("Testing conjur_host_identity role") {
          steps {
            sh './ci/test.sh -v 6 -d conjur_host_identity'
            junit 'roles/conjur_host_identity/tests/junit/*'
          }
        }

        stage("Running conjur_variable unit tests") {
          steps {
            sh './dev/test_unit.sh -r'
            publishHTML (target : [allowMissing: false,
              alwaysLinkToLastBuild: false,
              keepAll: true,
              reportDir: 'tests/output/reports/coverage=units/',
              reportFiles: 'index.html',
              reportName: 'Ansible Coverage Report',
              reportTitles: 'Conjur Ansible Collection report'])
          }
        }
      }
    }

    stage('Run Enterprise tests') {
      stages {
        stage("Test conjur_variable lookup plugin") {
          steps {
            sh './ci/test.sh -e -d conjur_variable'
            junit 'tests/conjur_variable/junit/*'
          }
        }

        stage("Test conjur_host_identity role") {
          steps {
            sh './ci/test.sh -e -d conjur_host_identity'
            junit 'roles/conjur_host_identity/tests/junit/*'
          }
        }
      }
    }

    stage('Build Release Artifacts') {
      when {
        anyOf {
            branch 'master'
            buildingTag()
        }
      }

      steps {
        sh './ci/build_release'
        archiveArtifacts 'cyberark-conjur-*.tar.gz'
      }
    }

    stage('Publish to Ansible Galaxy') {
      when {
        buildingTag()
      }

      steps {
        sh 'summon ./ci/publish_to_galaxy'
      }
    }
  }

  post {
    always {
      cleanupAndNotify(currentBuild.currentResult)
    }
  }
}
