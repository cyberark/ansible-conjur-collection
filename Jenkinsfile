#!/usr/bin/env groovy

pipeline {
  agent { label 'executor-v2' }

  options {
    timestamps()
    buildDiscarder(logRotator(numToKeepStr: '30'))
  }

  triggers {
    cron(getDailyCronString())
  }

  stages {
    stage('Validate') {
      parallel {
        stage('Changelog') {
          steps { parseChangelog() }
        }
      }
    }

    stage('Run conjur_variable unit tests') {
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

    stage('Run integration tests with Conjur Open Source') {
      stages {
        stage('Ansible v8 (core 2.15) - latest') {
          stages {
            stage('Deploy Conjur') {
              steps {
                sh './dev/start.sh -v 8'
              }
            }
            stage('Run tests') {
              parallel {
                stage('Testing conjur_variable lookup plugin') {
                  steps {
                    sh './ci/test.sh -d -t conjur_variable'
                    junit 'tests/conjur_variable/junit/*'
                  }
                }

                stage('Testing conjur_host_identity role') {
                  steps {
                    sh './ci/test.sh -d -t conjur_host_identity'
                    junit 'roles/conjur_host_identity/tests/junit/*'
                  }
                }
              }
            }
          }
        }

        stage('Ansible v7 (core 2.14)') {
          when {
            anyOf {
              branch 'main'
              buildingTag()
            }
          }
          stages {
            stage('Deploy Conjur') {
              steps {
                sh './dev/start.sh -v 7'
              }
            }
            stage('Run tests') {
              parallel {
                stage('Testing conjur_variable lookup plugin') {
                  steps {
                    sh './ci/test.sh -d -t conjur_variable'
                    junit 'tests/conjur_variable/junit/*'
                  }
                }

                stage('Testing conjur_host_identity role') {
                  steps {
                    sh './ci/test.sh -d -t conjur_host_identity'
                    junit 'roles/conjur_host_identity/tests/junit/*'
                  }
                }
              }
            }
          }
        }

        stage('Ansible v6 (core 2.13)') {
          when {
            anyOf {
              branch 'main'
              buildingTag()
            }
          }
          stages {
            stage('Deploy Conjur') {
              steps {
                sh './dev/start.sh -v 6'
              }
            }
            stage('Run tests') {
              parallel {
                stage('Testing conjur_variable lookup plugin') {
                  steps {
                    sh './ci/test.sh -d -t conjur_variable'
                    junit 'tests/conjur_variable/junit/*'
                  }
                }

                stage('Testing conjur_host_identity role') {
                  steps {
                    sh './ci/test.sh -d -t conjur_host_identity'
                    junit 'roles/conjur_host_identity/tests/junit/*'
                  }
                }
              }
            }
          }
        }
      }
    }

    stage('Run integration tests with Conjur Enterprise') {
      stages {
        stage('Deploy Conjur Enterprise') {
          steps {
            sh './dev/start.sh -e -v 8'
          }
        }
        stage('Run tests') {
          parallel {
            stage("Testing conjur_variable lookup plugin") {
              steps {
                sh './ci/test.sh -d -t conjur_variable'
                junit 'tests/conjur_variable/junit/*'
              }
            }

            stage("Testing conjur_host_identity role") {
              steps {
                sh './ci/test.sh -d -t conjur_host_identity'
                junit 'roles/conjur_host_identity/tests/junit/*'
              }
            }
          }
        }
      }
    }
    stages {
    stage('Get InfraPool ExecutorV2 Agent') {
      steps {
        script {
          INFRAPOOL_EXECUTORV2_AGENT_0 = getInfraPoolAgent.connected(type: "ExecutorV2", quantity: 1, duration: 1)[0]
        }
      }
    }
    stage('Create a Tenant') {
      steps {
        script {
          TENANT = getConjurCloudTenant()
        }
      }
    }
    stage('Authenticate') {
      steps {
        script {
          def id_token = getConjurCloudTenant.tokens(
            infrapool: INFRAPOOL_EXECUTORV2_AGENT_0,
            identity_url: "${TENANT.identity_information.idaptive_tenant_fqdn}",
            username: "${TENANT.login_name}",
          )
 
          def conj_token = getConjurCloudTenant.tokens(
            infrapool: INFRAPOOL_EXECUTORV2_AGENT_0,
            conjur_url: "${TENANT.conjur_cloud_url}",
            identity_token: "${id_token}"
            )
        }
      }
    }
  }

    stage('Build Release Artifacts') {
      when {
        anyOf {
            branch 'main'
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
      script {
        deleteConjurCloudTenant("${TENANT.id}")
      }
      cleanupAndNotify(currentBuild.currentResult)
    }
  }
}