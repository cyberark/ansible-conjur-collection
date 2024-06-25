#!/usr/bin/env groovy
@Library("product-pipelines-shared-library") _

// Automated release, promotion and dependencies
properties([
  // Include the automated release parameters for the build
  release.addParams(),
  // Dependencies of the project that should trigger builds
  dependencies([])
])

// Performs release promotion.  No other stages will be run
if (params.MODE == "PROMOTE") {
  release.promote(params.VERSION_TO_PROMOTE) { sourceVersion, targetVersion, assetDirectory ->

  }
  // Copy Github Enterprise release to Github
  release.copyEnterpriseRelease(params.VERSION_TO_PROMOTE)
  return
}

pipeline {
  agent { label 'conjur-enterprise-common-agent' }

  options {
    timestamps()
    buildDiscarder(logRotator(numToKeepStr: '30'))
  }

  triggers {
    cron(getDailyCronString())
  }

  environment {
    MODE = release.canonicalizeMode()
  }


  stages {
    stage('Scan for internal URLs') {
      steps {
        script {
          detectInternalUrls()
        }
      }
    }

    stage('Get InfraPool ExecutorV2 Agent') {
      steps {
        script {
          // Request ExecutorV2 agents for 1 hour(s)
          INFRAPOOL_EXECUTORV2_AGENTS = getInfraPoolAgent(type: "ExecutorV2", quantity: 1, duration: 1)
          INFRAPOOL_EXECUTORV2_AGENT_0 = INFRAPOOL_EXECUTORV2_AGENTS[0]
          infrapool = infraPoolConnect(INFRAPOOL_EXECUTORV2_AGENT_0, {})
        }
      }
    }

    // Generates a VERSION file based on the current build number and latest version in CHANGELOG.md
    stage('Validate Changelog and set version') {
      steps {
        script {
          updateVersion(infrapool, "CHANGELOG.md", "${BUILD_NUMBER}")
        }
      }
    }

    stage('Run Conjur Cloud tests') {
      stages {
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
                infrapool: infrapool,
                identity_url: "${TENANT.identity_information.idaptive_tenant_fqdn}",
                username: "${TENANT.login_name}"
              )

              def conj_token = getConjurCloudTenant.tokens(
                infrapool: infrapool,
                conjur_url: "${TENANT.conjur_cloud_url}",
                identity_token: "${id_token}"
                )

              env.conj_token = conj_token
            }
          }
        }
        stage('Run tests against Tenant') {
          environment {
            INFRAPOOL_CONJUR_APPLIANCE_URL="${TENANT.conjur_cloud_url}"
            INFRAPOOL_CONJUR_AUTHN_LOGIN="${TENANT.login_name}"
            INFRAPOOL_CONJUR_AUTHN_TOKEN="${env.conj_token}"
            INFRAPOOL_TEST_CLOUD=true
          }
          steps {
            script {
              infrapool.agentSh "./dev/start.sh -c -v 8"
            }
          }
        }
        stage('Ansible v8 (core 2.15) - latest') {
          stages {
            stage('Run tests') {
              parallel {
                stage('Testing conjur_variable lookup plugin') {
                  steps {
                    script {
                      infrapool.agentSh './ci/test.sh -d -t conjur_variable'
                    }
                  }
                  post {
                    always {
                      script {
                        infrapool.agentStash name: 'conjur_variable', includes: 'tests/conjur_variable/junit/*'
                        unstash 'conjur_variable'
                        junit 'tests/conjur_variable/junit/*'
                      }
                    }
                  }
                }
                stage('Testing conjur_host_identity role') {
                  steps {
                    script {
                      infrapool.agentSh './ci/test.sh -d -t conjur_host_identity'
                    }
                  }
                  post {
                    always {
                      script {
                        infrapool.agentStash name: 'conjur_host_identity', includes: 'roles/conjur_host_identity/tests/junit/*'
                        unstash 'conjur_host_identity'
                        junit 'roles/conjur_host_identity/tests/junit/*'
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }


  post {
    always {
      script {
            deleteConjurCloudTenant("${TENANT.id}")
      }
      releaseInfraPoolAgent(".infrapool/release_agents")
    }
  }
}
