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
  release.promote(params.VERSION_TO_PROMOTE) { infrapool, sourceVersion, targetVersion, assetDirectory ->

    infrapool.agentSh """
      ls "${assetDirectory}"
      cp "${assetDirectory}/cyberark-conjur-${targetVersion}.tar.gz" ./cyberark-conjur-${targetVersion}.tar.gz

      export TAG="v${targetVersion}"
      summon ./ci/publish_to_galaxy
    """

  }
  release.copyEnterpriseRelease(params.VERSION_TO_PROMOTE)
  return
}

pipeline {
  agent { label 'conjur-enterprise-common-agent' }

  options {
    timestamps()
    buildDiscarder(logRotator(numToKeepStr: '30'))
  }

  environment {
    MODE = release.canonicalizeMode()
    ANSIBLE_VERSION = 'stable-2.18' 
    PYTHON_VERSION = '3.13' 
  }

  triggers {
    cron(getDailyCronString())
    parameterizedCron(getWeeklyCronString("H(1-5)","%MODE=RELEASE"))
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
          // Request InfraPool
          INFRAPOOL_EXECUTORV2_AGENTS = getInfraPoolAgent(type: "ExecutorV2", quantity: 1, duration: 2)
          INFRAPOOL_EXECUTORV2_AGENT_0 = INFRAPOOL_EXECUTORV2_AGENTS[0]
          infrapool = infraPoolConnect(INFRAPOOL_EXECUTORV2_AGENT_0, {})
          INFRAPOOL_AZURE_EXECUTORV2_AGENT_0 = getInfraPoolAgent.connected(type: "AzureExecutorV2", quantity: 1, duration: 2)[0]
          INFRAPOOL_GCP_EXECUTORV2_AGENT_0 = getInfraPoolAgent.connected(type: "GcpExecutorV2", quantity: 1, duration: 2)[0]
        }
      }
    }

    // Generates a VERSION file based on the current build number and latest version in CHANGELOG.md
    stage('Validate Changelog and set version') {
      steps {
        script {
          updateVersion(infrapool, "CHANGELOG.md", "${BUILD_NUMBER}")
          updateVersion(INFRAPOOL_AZURE_EXECUTORV2_AGENT_0, "CHANGELOG.md", "${BUILD_NUMBER}")
          updateVersion(INFRAPOOL_GCP_EXECUTORV2_AGENT_0, "CHANGELOG.md", "${BUILD_NUMBER}")
        }
      }
    }
    stage ('Run conjur_variable unit tests') {
      steps {
        script {
          infrapool.agentSh './dev/test_unit.sh -r'
          infrapool.agentStash name: 'junit-xml', includes: 'tests/output/junit/*.xml'
          infrapool.agentStash name: 'coverage-xml', includes: 'tests/output/reports/*.xml'
        }
      }
      post {
        always {
          unstash 'junit-xml'
          unstash 'coverage-xml'
          junit 'tests/output/junit/*.xml'
          cobertura autoUpdateHealth: false, autoUpdateStability: false, coberturaReportFile: 'tests/output/reports/coverage=units.xml', conditionalCoverageTargets: '30, 0, 0', failUnhealthy: false, failUnstable: false, lineCoverageTargets: '30, 0, 0', maxNumberOfBuilds: 0, methodCoverageTargets: '30, 0, 0', onlyStable: false, sourceEncoding: 'ASCII', zoomCoverageChart: false
          codacy action: 'reportCoverage', filePath: "tests/output/reports/coverage=units.xml"
        }
      }
    }

    stage('Run conjur_variable sanity tests') {
      parallel {
        stage ('Run ansible-lint') {
          steps {
            script {
              runAnsibleLint()
            }
          }
        }
        stage('conjur_variable sanity tests for Ansible core 2.16') {
          steps {
            script {
              runSanityTests('stable-2.16', '3.12')
            }
          }
        }
        stage('conjur_variable sanity tests for Ansible core 2.17') {
          steps {
            script {
              runSanityTests('stable-2.17', '3.12')
            }
          }
        }
        stage('conjur_variable sanity tests for Ansible core 2.18') {
          steps {
            script {
              runSanityTests('stable-2.18', '3.13')
            }
          }
        }
        stage('conjur_variable sanity tests for Ansible core (2.19) - default') {
          steps {
            script {
              runSanityTestsDefault()
            }
            publishHTML (target : [allowMissing: false,
            alwaysLinkToLastBuild: false,
            keepAll: true,
            reportDir: 'tests/output/reports/coverage=sanity/',
            reportFiles: 'index.html',
            reportName: 'Ansible Sanity Coverage Report',
            reportTitles: 'Conjur Ansible Collection sanity report'])
          }
        }
      }
    }
    
    stage('Run API Key integration tests with Conjur Open Source') {
      stages {
        stage('Ansible v10 (core 2.17) - latest') {
          stages {
            stage('Deploy Conjur') {
              steps {
                script {
                  infrapool.agentSh './dev/start.sh -f oss -a api_key -v 10 -p 3.12'
                }
              }
            }
            stage('Run tests') {
              parallel {
                stage('Testing conjur_variable lookup plugin') {
                  steps {
                    script {
                      infrapool.agentSh './ci/test.sh -u api_key -d -t conjur_variable'
                    }
                  }
                  post {
                    always {
                      script {
                        handleJunitReports('conjur_variable', 'tests/conjur_variable/junit/*')
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
                        handleJunitReports('conjur_host_identity', 'roles/conjur_host_identity/tests/junit/*')
                      }
                    }
                  }
                }
              }
            }
          }
        }

        stage('Ansible v11 (core 2.18) - latest') {
          stages {
            stage('Deploy Conjur') {
              steps {
                script {
                  infrapool.agentSh './dev/start.sh -f oss -a api_key -v 11 -p 3.13'
                }
              }
            }
            stage('Run tests') {
              parallel {
                stage('Testing conjur_variable lookup plugin') {
                  steps {
                    script {
                      infrapool.agentSh './ci/test.sh -u api_key -d -t conjur_variable'
                    }
                  }
                  post {
                    always {
                      script {
                        handleJunitReports('conjur_variable', 'tests/conjur_variable/junit/*')
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
                        handleJunitReports('conjur_host_identity', 'roles/conjur_host_identity/tests/junit/*')
                      }
                    }
                  }
                }
              }
            }
          }
        }

        stage('Ansible v12 (core 2.19) - latest') {
          stages {
            stage('Deploy Conjur') {
              steps {
                script {
                  infrapool.agentSh './dev/start.sh -f oss -a api_key -v 12 -p 3.13'
                }
              }
            }
            stage('Run tests') {
              parallel {
                stage('Testing conjur_variable lookup plugin') {
                  steps {
                    script {
                      infrapool.agentSh './ci/test.sh -u api_key -d -t conjur_variable'
                    }
                  }
                  post {
                    always {
                      script {
                        handleJunitReports('conjur_variable', 'tests/conjur_variable/junit/*')
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
                        handleJunitReports('conjur_host_identity', 'roles/conjur_host_identity/tests/junit/*')
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

    stage('Run API Key integration tests with Conjur Enterprise') {
      stages {
        stage('Ansible v11 (core 2.18) - latest') {
          stages {
            stage('Deploy Conjur Enterprise') {
              steps {
                script {
                  infrapool.agentSh './dev/start.sh -f enterprise -a api_key  -v 11 -p 3.12'
                }
              }
            }
            stage('Run tests') {
              parallel {
                stage("Testing conjur_variable lookup plugin") {
                  steps {
                    script {
                      infrapool.agentSh './ci/test.sh -u api_key -d -t conjur_variable'
                    }
                  }
                  post {
                    always {
                      script {
                        handleJunitReports('conjur_variable', 'tests/conjur_variable/junit/*')
                      }
                    }
                  }
                }
                stage("Testing conjur_host_identity role") {
                  steps {
                    script {
                      infrapool.agentSh './ci/test.sh -d -t conjur_host_identity'
                    }
                  }
                  post {
                    always {
                      script {
                        handleJunitReports('conjur_host_identity', 'roles/conjur_host_identity/tests/junit/*')
                      }
                    }
                  }
                }
              }
            }
          }
        }

        stage('Ansible v12 (core 2.19) - latest') {
          stages {
            stage('Deploy Conjur Enterprise') {
              steps {
                script {
                  infrapool.agentSh './dev/start.sh -f enterprise -a api_key  -v 12 -p 3.12'
                }
              }
            }
            stage('Run tests') {
              parallel {
                stage("Testing conjur_variable lookup plugin") {
                  steps {
                    script {
                      infrapool.agentSh './ci/test.sh -u api_key -d -t conjur_variable'
                    }
                  }
                  post {
                    always {
                      script {
                        handleJunitReports('conjur_variable', 'tests/conjur_variable/junit/*')
                      }
                    }
                  }
                }
                stage("Testing conjur_host_identity role") {
                  steps {
                    script {
                      infrapool.agentSh './ci/test.sh -d -t conjur_host_identity'
                    }
                  }
                  post {
                    always {
                      script {
                        handleJunitReports('conjur_host_identity', 'roles/conjur_host_identity/tests/junit/*')
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
    
    stage('Run IAM integration tests with Conjur OSS') {
      stages {
        stage('Ansible v11 (core 2.18) - latest') {
          stages {
            stage('Deploy Conjur OSS for IAM') {
              steps {
                script {
                  infrapool.agentSh './dev/start.sh -f oss -a iam  -v 11 -p 3.13'
                }
              }
            }
            stage("Testing conjur_variable lookup plugin for IAM") {
              steps {
                script {
                  infrapool.agentSh './ci/test.sh -u iam -d -t conjur_variable'
                }
              }
            }
          }
        }

        stage('Ansible v12 (core 2.19) - latest') {
          stages {
            stage('Deploy Conjur OSS for IAM') {
              steps {
                script {
                  infrapool.agentSh './dev/start.sh -f oss -a iam  -v 12 -p 3.13'
                }
              }
            }
            stage("Testing conjur_variable lookup plugin for IAM") {
              steps {
                script {
                  infrapool.agentSh './ci/test.sh -u iam -d -t conjur_variable'
                }
              }
            }
          }
        }
      }
    }

    stage('Run IAM integration tests with Conjur Enterprise') {
      stages {
        stage('Ansible v11 (core 2.18) - latest') {
          stages {
            stage('Deploy Conjur Enterprise for IAM') {
              steps {
                script {
                  infrapool.agentSh './dev/start.sh -f enterprise -a iam  -v 11 -p 3.12'
                }
              }
            }
            stage("Testing conjur_variable lookup plugin for IAM") {
              steps {
                script {
                  infrapool.agentSh './ci/test.sh -u iam -d -t conjur_variable'
                }
              }
            }
          }
        }

        stage('Ansible v12 (core 2.19) - latest') {
          stages {
            stage('Deploy Conjur Enterprise for IAM') {
              steps {
                script {
                  infrapool.agentSh './dev/start.sh -f enterprise -a iam  -v 12 -p 3.12'
                }
              }
            }
            stage("Testing conjur_variable lookup plugin for IAM") {
              steps {
                script {
                  infrapool.agentSh './ci/test.sh -u iam -d -t conjur_variable'
                }
              }
            }
          }
        }
      }
    }

    stage('Run Azure integration tests with Conjur OSS') {
      stages {
        stage('Ansible v11 (core 2.18) - latest') {
          stages {
            stage('Deploy Conjur OSS for Azure') {
              steps {
                script {
                  INFRAPOOL_AZURE_EXECUTORV2_AGENT_0.agentSh 'summon ./dev/start.sh -f oss -a azure -v 11 -p 3.13'
                }
              }
            }
            stage("Testing conjur_variable lookup plugin for Azure") {
              steps {
                script {
                  INFRAPOOL_AZURE_EXECUTORV2_AGENT_0.agentSh 'summon ./ci/test.sh -u azure -d -t conjur_variable'
                }
              }
            }
          }
        }

        stage('Ansible v12 (core 2.19) - latest') {
          stages {
            stage('Deploy Conjur OSS for Azure') {
              steps {
                script {
                  INFRAPOOL_AZURE_EXECUTORV2_AGENT_0.agentSh 'summon ./dev/start.sh -f oss -a azure -v 12 -p 3.13'
                }
              }
            }
            stage("Testing conjur_variable lookup plugin for Azure") {
              steps {
                script {
                  INFRAPOOL_AZURE_EXECUTORV2_AGENT_0.agentSh 'summon ./ci/test.sh -u azure -d -t conjur_variable'
                }
              }
            }
          }
        }
      }
    }
    stage('Run Azure integration tests with Conjur Enterprise') {
      stages {
        stage('Ansible v11 (core 2.18) - latest') {
          stages {
            stage('Deploy Conjur Enterprise for Azure') {
              steps {
                script {
                  INFRAPOOL_AZURE_EXECUTORV2_AGENT_0.agentSh 'summon ./dev/start.sh -f enterprise -a azure -v 11 -p 3.12'
                }
              }
            }
            stage("Testing conjur_variable lookup plugin for Azure") {
              steps {
                script {
                  INFRAPOOL_AZURE_EXECUTORV2_AGENT_0.agentSh 'summon ./ci/test.sh -u azure -d -t conjur_variable'
                }
              }
            }
          }
        }

        stage('Ansible v12 (core 2.19) - latest') {
          stages {
            stage('Deploy Conjur Enterprise for Azure') {
              steps {
                script {
                  INFRAPOOL_AZURE_EXECUTORV2_AGENT_0.agentSh 'summon ./dev/start.sh -f enterprise -a azure -v 12 -p 3.12'
                }
              }
            }
            stage("Testing conjur_variable lookup plugin for Azure") {
              steps {
                script {
                  INFRAPOOL_AZURE_EXECUTORV2_AGENT_0.agentSh 'summon ./ci/test.sh -u azure -d -t conjur_variable'
                }
              }
            }
          }
        }
      }
    }

    stage('Generate GCP token for Conjur OSS') {
      steps {
        script {
          INFRAPOOL_GCP_EXECUTORV2_AGENT_0.agentSh './dev/get_gcp_token.sh host/gcp-apps/test-app cucumber'
          INFRAPOOL_GCP_EXECUTORV2_AGENT_0.agentStash name: 'token-out', includes: 'dev/gcp/*'
        }
      }
    }

    stage('Run GCP integration tests with Conjur OSS') {
      stages {
        stage('Deploy Conjur OSS for GCP') {
          steps {
            script {
              infrapool.agentUnstash name: 'token-out'
              infrapool.agentSh './dev/start.sh -f oss -a gcp  -v 11 -p 3.13'
            }
          }
        }
        stage("Testing conjur_variable lookup plugin for GCP") {
          steps {
            script {
              infrapool.agentSh './ci/test.sh -u gcp -d -t conjur_variable'
            }
          }
        }
      }
    }

    stage('Generate GCP token for Conjur Enterprise') {
      steps {
        script {
          INFRAPOOL_GCP_EXECUTORV2_AGENT_0.agentSh './dev/get_gcp_token.sh host/gcp-apps/test-app demo'
          INFRAPOOL_GCP_EXECUTORV2_AGENT_0.agentStash name: 'token-out-enterprise', includes: 'dev/gcp/*'
        }
      }
    }

    stage('Run GCP integration tests with Conjur Enterprise') {
      stages {
        stage('Deploy Conjur Enterprise for GCP') {
          steps {
            script {
              infrapool.agentUnstash name: 'token-out-enterprise'
              infrapool.agentSh './dev/start.sh -f enterprise -a gcp  -v 11 -p 3.12'
            }
          }
        }
        stage("Testing conjur_variable lookup plugin for GCP") {
          steps {
            script {
              infrapool.agentSh './ci/test.sh -u gcp -d -t conjur_variable'
            }
          }
        }
      }
    }

    stage('Delete the Running Docker containers') {
      steps {
        script {
          infrapool.agentSh 'docker rm -f $(docker ps -aq)'
          INFRAPOOL_AZURE_EXECUTORV2_AGENT_0.agentSh 'docker rm -f $(docker ps -aq)'
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
        stage('Get Edge Token') {
          steps {
            script {
              def edge_token = getConjurCloudTenant.tokens(
                infrapool: infrapool,
                conjur_url: "${TENANT.conjur_cloud_url}",
                edge_name: "${TENANT.conjur_edge_name}",
                conjur_token: "${conj_token}"
              )

              def deploy_edge = getConjurCloudTenant.edge(
                infrapool: infrapool,
                conjur_url: "${TENANT.conjur_cloud_url}",
                edge_name: "edge-test",
                edge_token: "${edge_token}",
                common_name: "edge-test",
                subject_alt_names: "edge-test"
              )

              env.edge_token = edge_token
            }
          }
        }
        stage('Run API Key tests against Cloud Tenant') {
          environment {
            INFRAPOOL_CONJUR_APPLIANCE_URL="${TENANT.conjur_cloud_url}"
            INFRAPOOL_CONJUR_AUTHN_LOGIN="${TENANT.login_name}"
            INFRAPOOL_CONJUR_AUTHN_TOKEN="${env.conj_token}"
            INFRAPOOL_TEST_CLOUD=true
          }
          steps {
            script {
              infrapool.agentSh "./dev/start.sh -f cloud -a api_key -v 11 -p 3.13"
            }
          }
        }
        stage('Ansible v11 (core 2.18) for API Key - latest') {
          stages {
            stage('Run tests for API Key') {
              parallel {
                stage('Testing conjur_variable lookup plugin for API Key') {
                  steps {
                    script {
                      infrapool.agentSh './ci/test.sh -u api_key -d -t conjur_variable'
                    }
                  }
                  post {
                    always {
                      script {
                        handleJunitReports('conjur_variable', 'tests/conjur_variable/junit/*')
                      }
                    }
                  }
                }
                stage('Testing conjur_host_identity role for API Key') {
                  steps {
                    script {
                      infrapool.agentSh './ci/test.sh -d -t conjur_host_identity'
                    }
                  }
                  post {
                    always {
                      script {
                        handleJunitReports('conjur_host_identity', 'roles/conjur_host_identity/tests/junit/*')
                      }
                    }
                  }
                }
              }
            }
          }
        }
        stage('Testing Conjur Variable Lookup plugin for Api Key on Edge') {
          environment {
            INFRAPOOL_CONJUR_APPLIANCE_URL="${TENANT.conjur_cloud_url}"
            INFRAPOOL_CONJUR_AUTHN_LOGIN="${TENANT.login_name}"
            INFRAPOOL_CONJUR_AUTHN_TOKEN="${env.conj_token}"
            INFRAPOOL_TEST_CLOUD=true
          }
          steps {
            script {
              infrapool.agentSh "./dev/start.sh -f edge -a api_key -v 11 -p 3.13"
              infrapool.agentSh './ci/test.sh -u api_key -d -t conjur_variable'
            }
          }
        }

        stage('Run IAM tests against Cloud Tenant') {
          environment {
            INFRAPOOL_CONJUR_APPLIANCE_URL="${TENANT.conjur_cloud_url}"
            INFRAPOOL_CONJUR_AUTHN_LOGIN="${TENANT.login_name}"
            INFRAPOOL_CONJUR_AUTHN_TOKEN="${env.conj_token}"
            INFRAPOOL_TEST_CLOUD=true
          }
          steps {
            script {
              infrapool.agentSh "./dev/start.sh -f cloud -a iam -v 11 -p 3.13"
            }
          }
        }

        stage('Testing conjur_variable lookup plugin for IAM') {
          steps {
            script {
              infrapool.agentSh './ci/test.sh -u iam -d -t conjur_variable'
            }
          }
        }

        stage('Testing conjur_variable lookup plugin for IAM on Edge') {
          environment {
            INFRAPOOL_CONJUR_APPLIANCE_URL="${TENANT.conjur_cloud_url}"
            INFRAPOOL_CONJUR_AUTHN_LOGIN="${TENANT.login_name}"
            INFRAPOOL_CONJUR_AUTHN_TOKEN="${env.conj_token}"
            INFRAPOOL_TEST_CLOUD=true
          }
          steps {
            script {
              infrapool.agentSh "./dev/start.sh -f edge -a iam -v 11 -p 3.13"
              infrapool.agentSh './ci/test.sh -u iam -d -t conjur_variable'
            }
          }
        }

        stage('Generate GCP token for Conjur Cloud') {
          steps {
            script{
              INFRAPOOL_GCP_EXECUTORV2_AGENT_0.agentSh './dev/get_gcp_token.sh host/data/gcp-apps/test-app conjur'
              INFRAPOOL_GCP_EXECUTORV2_AGENT_0.agentStash name: 'token-out-cloud', includes: 'dev/gcp/*'
            }
          }
        }
        stage('Run GCP tests against Cloud Tenant') {
          environment {
            INFRAPOOL_CONJUR_APPLIANCE_URL="${TENANT.conjur_cloud_url}"
            INFRAPOOL_CONJUR_AUTHN_LOGIN="${TENANT.login_name}"
            INFRAPOOL_CONJUR_AUTHN_TOKEN="${env.conj_token}"
            INFRAPOOL_TEST_CLOUD=true
          }
          steps {
            script {
              infrapool.agentUnstash name: 'token-out-cloud'
              infrapool.agentSh "./dev/start.sh -f cloud -a gcp -v 11 -p 3.13"
            }
          }
        }

        stage('Testing conjur_variable lookup plugin for GCP') {
          steps {
            script {
              infrapool.agentSh './ci/test.sh -u gcp -d -t conjur_variable'
            }
          }
        }

        stage('Testing conjur_variable lookup plugin for GCP on Edge') {
          environment {
            INFRAPOOL_CONJUR_APPLIANCE_URL="${TENANT.conjur_cloud_url}"
            INFRAPOOL_CONJUR_AUTHN_LOGIN="${TENANT.login_name}"
            INFRAPOOL_CONJUR_AUTHN_TOKEN="${env.conj_token}"
            INFRAPOOL_TEST_CLOUD=true
          }
          steps {
            script {
              infrapool.agentUnstash name: 'token-out-cloud'
              infrapool.agentSh "./dev/start.sh -f edge -a gcp -v 11 -p 3.13"
              infrapool.agentSh './ci/test.sh -u gcp -d -t conjur_variable'
            }
          }
        }
        stage('Get Edge Token for Azure') {
          steps {
            script {
              def edge_token = getConjurCloudTenant.tokens(
                infrapool: infrapool,
                conjur_url: "${TENANT.conjur_cloud_url}",
                edge_name: "${TENANT.conjur_edge_name}",
                conjur_token: "${conj_token}"
              )

              def deploy_edge = getConjurCloudTenant.edge(
                infrapool:  INFRAPOOL_AZURE_EXECUTORV2_AGENT_0,,
                conjur_url: "${TENANT.conjur_cloud_url}",
                edge_name: "edge-test",
                edge_token: "${edge_token}",
                common_name: "edge-test",
                subject_alt_names: "edge-test"
              )

              env.edge_token = edge_token
            }
          }
        }
        stage('Run Azure tests against Cloud Tenant') {
          environment {
            INFRAPOOL_CONJUR_APPLIANCE_URL="${TENANT.conjur_cloud_url}"
            INFRAPOOL_CONJUR_AUTHN_LOGIN="${TENANT.login_name}"
            INFRAPOOL_CONJUR_AUTHN_TOKEN="${env.conj_token}"
            INFRAPOOL_TEST_CLOUD=true
          }
          steps {
            script {
              INFRAPOOL_AZURE_EXECUTORV2_AGENT_0.agentSh"summon ./dev/start.sh -f cloud -a azure -v 11 -p 3.13"
            }
          }
        }

        stage('Testing conjur_variable lookup plugin for Azure') {
          steps {
            script {
              INFRAPOOL_AZURE_EXECUTORV2_AGENT_0.agentSh 'summon ./ci/test.sh -u azure -d -t conjur_variable'
            }
          }
        }
        
        stage('Testing conjur_variable lookup plugin for Azure on Edge') {
          environment {
            INFRAPOOL_CONJUR_APPLIANCE_URL="${TENANT.conjur_cloud_url}"
            INFRAPOOL_CONJUR_AUTHN_LOGIN="${TENANT.login_name}"
            INFRAPOOL_CONJUR_AUTHN_TOKEN="${env.conj_token}"
            INFRAPOOL_TEST_CLOUD=true
          }
          steps {
            script {
              INFRAPOOL_AZURE_EXECUTORV2_AGENT_0.agentSh "summon ./dev/start.sh -f edge -a azure -v 11 -p 3.13"
              INFRAPOOL_AZURE_EXECUTORV2_AGENT_0.agentSh 'summon ./ci/test.sh -u azure -d -t conjur_variable'
            }
          }
        }
      }
    }
    stage('Build artifacts') {
      steps {
        script {
          infrapool.agentSh './ci/build_release'
        }
      }
    }
    stage('Release') {
      when {
        expression {
          MODE == "RELEASE"
        } 
      }
      steps {
        script {
          release(infrapool) { billOfMaterialsDirectory, assetDirectory, toolsDirectory ->
            // Publish release artifacts to all the appropriate locations
            // Copy any artifacts to assetDirectory to attach them to the Github release
            infrapool.agentSh "cp cyberark-conjur-*.tar.gz  ${assetDirectory}"
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

def runAnsibleLint() {
    infrapool.agentSh './dev/lint.sh'
}

def runSanityTests(version, pythonVersion) {
    infrapool.agentSh "./dev/test_sanity.sh -a ${version} -p ${pythonVersion}"
}

def runSanityTestsDefault() {
    infrapool.agentSh './dev/test_sanity.sh -r'
    infrapool.agentStash name: 'sanity-test-report', includes: 'tests/output/reports/coverage=sanity/*'
    unstash 'sanity-test-report'
}

def handleJunitReports(stashName, testFilesPattern) {
    infrapool.agentStash name: stashName, includes: testFilesPattern
    unstash stashName
    junit testFilesPattern
}