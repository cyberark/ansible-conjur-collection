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

LATEST_ANSIBLE_VERSION = "12"

pipeline {
  agent { label 'conjur-enterprise-common-agent' }

  options {
    timestamps()
    buildDiscarder(logRotator(numToKeepStr: '30'))
  }

  environment {
    MODE = release.canonicalizeMode()
    ANSIBLE_VERSION = 'stable-2.19'
    PYTHON_VERSION = '3.13'
  }

  triggers {
    parameterizedCron("""
      ${getDailyCronString("%TEST_CLOUD=true")}
      ${getWeeklyCronString("H(1-5)", "%MODE=RELEASE")}
    """)
  }

  parameters {
    booleanParam(name: 'TEST_CLOUD', defaultValue: false, description: 'Run integration tests against a Conjur Cloud tenant')
  }

  stages {
    stage('Scan for internal URLs') {
      steps {
        script {
          detectInternalUrls()
        }
      }
    }

    stage('Get InfraPool ExecutorV2 Agents For Parallel Execution') {
      steps {
        script {
          INFRAPOOL_EXECUTORV2_AGENT_1 = getInfraPoolAgent.connected(type: "ExecutorV2", quantity: 1, duration: 2)[0]
          INFRAPOOL_EXECUTORV2_AGENT_2 = getInfraPoolAgent.connected(type: "ExecutorV2", quantity: 1, duration: 2)[0]

          INFRAPOOL_AZURE_EXECUTORV2_AGENT_1 = getInfraPoolAgent.connected(type: "AzureExecutorV2", quantity: 1, duration: 2)[0]
          INFRAPOOL_AZURE_EXECUTORV2_AGENT_2 = getInfraPoolAgent.connected(type: "AzureExecutorV2", quantity: 1, duration: 2)[0]

          INFRAPOOL_GCP_EXECUTORV2_AGENT_1 = getInfraPoolAgent.connected(type: "GcpExecutorV2", quantity: 1, duration: 2)[0]
          INFRAPOOL_GCP_EXECUTORV2_AGENT_2 = getInfraPoolAgent.connected(type: "GcpExecutorV2", quantity: 1, duration: 2)[0]
        }
      }
    }

    // Generates a VERSION file based on the current build number and latest version in CHANGELOG.md
    stage('Validate Changelog and set version') {
      steps {
        script {
          updateVersion(INFRAPOOL_EXECUTORV2_AGENT_1, "CHANGELOG.md", "${BUILD_NUMBER}")
          updateVersion(INFRAPOOL_EXECUTORV2_AGENT_2, "CHANGELOG.md", "${BUILD_NUMBER}")
          updateVersion(INFRAPOOL_AZURE_EXECUTORV2_AGENT_1, "CHANGELOG.md", "${BUILD_NUMBER}")
          updateVersion(INFRAPOOL_AZURE_EXECUTORV2_AGENT_2, "CHANGELOG.md", "${BUILD_NUMBER}")
          updateVersion(INFRAPOOL_GCP_EXECUTORV2_AGENT_1, "CHANGELOG.md", "${BUILD_NUMBER}")
          updateVersion(INFRAPOOL_GCP_EXECUTORV2_AGENT_2, "CHANGELOG.md", "${BUILD_NUMBER}")
        }
      }
    }
    stage ('Run conjur_variable unit tests') {
      steps {
        script {
          INFRAPOOL_EXECUTORV2_AGENT_1.agentSh './dev/test_unit.sh -r'
          INFRAPOOL_EXECUTORV2_AGENT_1.agentStash name: 'junit-xml', includes: 'tests/output/junit/*.xml'
          INFRAPOOL_EXECUTORV2_AGENT_1.agentStash name: 'coverage-xml', includes: 'tests/output/reports/*.xml'
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
              runAnsibleLint(INFRAPOOL_EXECUTORV2_AGENT_1)
            }
          }
        }

        stage('conjur_variable sanity tests for Ansible core 2.17') {
          steps {
            script {
              runSanityTests(INFRAPOOL_EXECUTORV2_AGENT_1, 'stable-2.17', '3.12')
            }
          }
        }

        stage('conjur_variable sanity tests for Ansible core 2.18') {
          steps {
            script {
              runSanityTests(INFRAPOOL_EXECUTORV2_AGENT_1, 'stable-2.18', '3.13')
            }
          }
        }

        stage('conjur_variable sanity tests for Ansible core (2.19) - default') {
          steps {
            script {
              runSanityTestsDefault(INFRAPOOL_EXECUTORV2_AGENT_1)
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

    stage('API Key Integration Tests') {
      stages {
        stage('Run API Key Integration Tests with Conjur OSS') {
          steps {
            parallel(
                    "Ansible 11": {
                      runApiKeyIntegrationTests(INFRAPOOL_EXECUTORV2_AGENT_1, '11', 'oss', '3.12')
                    },
                    "Ansible 12": {
                      runApiKeyIntegrationTests(INFRAPOOL_EXECUTORV2_AGENT_2, LATEST_ANSIBLE_VERSION, 'oss', '3.12')
                    }
            )
          }
          post {
            always {
              script {
                handleJunitReports(INFRAPOOL_EXECUTORV2_AGENT_1, 'conjur_variable', 'tests/conjur_variable/junit/*')
                handleJunitReports(INFRAPOOL_EXECUTORV2_AGENT_1, 'conjur_host_identity', 'roles/conjur_host_identity/tests/junit/*')

                handleJunitReports(INFRAPOOL_EXECUTORV2_AGENT_2, 'conjur_variable', 'tests/conjur_variable/junit/*')
                handleJunitReports(INFRAPOOL_EXECUTORV2_AGENT_2, 'conjur_host_identity', 'roles/conjur_host_identity/tests/junit/*')
              }
            }
          }
        }

        stage('Run API Key Integration Tests with Conjur Enterprise') {
          steps {
            parallel(
                    "Ansible 11": {
                      runApiKeyIntegrationTests(INFRAPOOL_EXECUTORV2_AGENT_1, '11', 'enterprise', '3.12')
                    },
                    "Ansible 12": {
                      runApiKeyIntegrationTests(INFRAPOOL_EXECUTORV2_AGENT_2, LATEST_ANSIBLE_VERSION, 'enterprise', '3.12')
                    }
            )
          }
        }
      }
    }

    stage('IAM Integration Tests') {
      stages {
        stage('Run IAM Integration Tests with Conjur OSS') {
          steps {
            parallel(
                    "Ansible 11": {
                      runIamIntegrationTests(INFRAPOOL_EXECUTORV2_AGENT_1, '11', 'oss', '3.12')
                    },
                    "Ansible 12": {
                      runIamIntegrationTests(INFRAPOOL_EXECUTORV2_AGENT_2, LATEST_ANSIBLE_VERSION, 'oss', '3.12')
                    }
            )
          }
        }

        stage('Run IAM Integration Tests with Conjur Enterprise') {
          steps {
            parallel(
                    "Ansible 11": {
                      runIamIntegrationTests(INFRAPOOL_EXECUTORV2_AGENT_1, '11', 'enterprise', '3.12')
                    },
                    "Ansible 12": {
                      runIamIntegrationTests(INFRAPOOL_EXECUTORV2_AGENT_2, LATEST_ANSIBLE_VERSION, 'enterprise', '3.12')
                    }
            )
          }
        }
      }
    }

    stage('Azure Integration Tests') {
      stages {
        stage('Run Azure Integration Tests with Conjur OSS') {
          steps {
            parallel(
                    "Ansible 11": {
                      runAzureIntegrationTests(INFRAPOOL_AZURE_EXECUTORV2_AGENT_1, '11', 'oss', '3.12')
                    },
                    "Ansible 12": {
                      runAzureIntegrationTests(INFRAPOOL_AZURE_EXECUTORV2_AGENT_2, LATEST_ANSIBLE_VERSION, 'oss', '3.12')
                    }
            )
          }
        }

        stage('Run Azure Integration Tests with Conjur Enterprise') {
          steps {
            parallel(
                    "Ansible 11": {
                      runAzureIntegrationTests(INFRAPOOL_AZURE_EXECUTORV2_AGENT_1, '11', 'enterprise', '3.12')
                    },
                    "Ansible 12": {
                      runAzureIntegrationTests(INFRAPOOL_AZURE_EXECUTORV2_AGENT_2, LATEST_ANSIBLE_VERSION, 'enterprise', '3.12')
                    }
            )
          }
        }
      }
    }

    stage('GCP Integration Tests') {
      stages {
        stage('Run GCP Integration Tests with Conjur OSS') {
          steps {
            parallel(
                    "Ansible 11": {
                      runGcpIntegrationTests(
                              INFRAPOOL_EXECUTORV2_AGENT_1,
                              INFRAPOOL_GCP_EXECUTORV2_AGENT_1,
                              '11',
                              'oss',
                              '3.12',
                              'cucumber',
                              'token-out'
                      )
                    },
                    "Ansible 12": {
                      runGcpIntegrationTests(
                              INFRAPOOL_EXECUTORV2_AGENT_2,
                              INFRAPOOL_GCP_EXECUTORV2_AGENT_2,
                              LATEST_ANSIBLE_VERSION,
                              'oss',
                              '3.12',
                              'cucumber',
                              'token-out'
                      )
                    }
            )
          }
        }

        stage('Run GCP Integration Tests with Conjur Enterprise') {
          steps {
            parallel(
                    "Ansible 11": {
                      runGcpIntegrationTests(
                              INFRAPOOL_EXECUTORV2_AGENT_1,
                              INFRAPOOL_GCP_EXECUTORV2_AGENT_1,
                              '11',
                              'enterprise',
                              '3.12',
                              'demo',
                              'token-out-enterprise'
                      )
                    },
                    "Ansible 12": {
                      runGcpIntegrationTests(
                              INFRAPOOL_EXECUTORV2_AGENT_2,
                              INFRAPOOL_GCP_EXECUTORV2_AGENT_2,
                              LATEST_ANSIBLE_VERSION,
                              'enterprise',
                              '3.12',
                              'demo',
                              'token-out-enterprise'
                      )
                    }
            )
          }
        }
      }
    }

    stage('Delete the Running Docker containers') {
      steps {
        script {
          INFRAPOOL_EXECUTORV2_AGENT_1.agentSh 'docker rm -f $(docker ps -aq)'
          INFRAPOOL_EXECUTORV2_AGENT_2.agentSh 'docker rm -f $(docker ps -aq)'
          INFRAPOOL_AZURE_EXECUTORV2_AGENT_1.agentSh 'docker rm -f $(docker ps -aq)'
          INFRAPOOL_AZURE_EXECUTORV2_AGENT_2.agentSh 'docker rm -f $(docker ps -aq)'
        }
      }
    }

    stage('Run Conjur Cloud tests') {
      when {
        expression { params.TEST_CLOUD }
      }
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
                      infrapool: INFRAPOOL_EXECUTORV2_AGENT_1,
                      identity_url: "${TENANT.identity_information.idaptive_tenant_fqdn}",
                      username: "${TENANT.login_name}"
              )

              def conj_token = getConjurCloudTenant.tokens(
                      infrapool: INFRAPOOL_EXECUTORV2_AGENT_1,
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
                      infrapool: INFRAPOOL_EXECUTORV2_AGENT_1,
                      conjur_url: "${TENANT.conjur_cloud_url}",
                      edge_name: "${TENANT.conjur_edge_name}",
                      conjur_token: "${conj_token}"
              )

              def deploy_edge = getConjurCloudTenant.edge(
                      infrapool: INFRAPOOL_EXECUTORV2_AGENT_1,
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
              INFRAPOOL_EXECUTORV2_AGENT_1.agentSh "./dev/start.sh -f cloud -a api_key -v ${LATEST_ANSIBLE_VERSION} -p 3.13"
            }
          }
        }
        stage('Ansible v12 for API Key - latest') {
          stages {
            stage('Run tests for API Key') {
              parallel {
                stage('Testing conjur_variable lookup plugin for API Key') {
                  steps {
                    script {
                      INFRAPOOL_EXECUTORV2_AGENT_1.agentSh './ci/test.sh -u api_key -d -t conjur_variable'
                    }
                  }
                  post {
                    always {
                      script {
                        handleJunitReports(INFRAPOOL_EXECUTORV2_AGENT_1, 'conjur_variable', 'tests/conjur_variable/junit/*')
                      }
                    }
                  }
                }
                stage('Testing conjur_host_identity role for API Key') {
                  steps {
                    script {
                      INFRAPOOL_EXECUTORV2_AGENT_1.agentSh './ci/test.sh -d -t conjur_host_identity'
                    }
                  }
                  post {
                    always {
                      script {
                        handleJunitReports(INFRAPOOL_EXECUTORV2_AGENT_1, 'conjur_host_identity', 'roles/conjur_host_identity/tests/junit/*')
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
              INFRAPOOL_EXECUTORV2_AGENT_1.agentSh "./dev/start.sh -f edge -a api_key -v ${LATEST_ANSIBLE_VERSION} -p 3.13"
              INFRAPOOL_EXECUTORV2_AGENT_1.agentSh './ci/test.sh -u api_key -d -t conjur_variable'
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
              INFRAPOOL_EXECUTORV2_AGENT_1.agentSh "./dev/start.sh -f cloud -a iam -v ${LATEST_ANSIBLE_VERSION} -p 3.13"
            }
          }
        }

        stage('Testing conjur_variable lookup plugin for IAM') {
          steps {
            script {
              INFRAPOOL_EXECUTORV2_AGENT_1.agentSh './ci/test.sh -u iam -d -t conjur_variable'
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
              INFRAPOOL_EXECUTORV2_AGENT_1.agentSh "./dev/start.sh -f edge -a iam -v ${LATEST_ANSIBLE_VERSION} -p 3.13"
              INFRAPOOL_EXECUTORV2_AGENT_1.agentSh './ci/test.sh -u iam -d -t conjur_variable'
            }
          }
        }

        stage('Generate GCP token for Conjur Cloud') {
          steps {
            script{
              INFRAPOOL_GCP_EXECUTORV2_AGENT_1.agentSh './dev/get_gcp_token.sh host/data/gcp-apps/test-app conjur'
              INFRAPOOL_GCP_EXECUTORV2_AGENT_1.agentStash name: 'token-out-cloud', includes: 'dev/gcp/*'
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
              INFRAPOOL_EXECUTORV2_AGENT_1.agentUnstash name: 'token-out-cloud'
              INFRAPOOL_EXECUTORV2_AGENT_1.agentSh "./dev/start.sh -f cloud -a gcp -v ${LATEST_ANSIBLE_VERSION} -p 3.13"
            }
          }
        }

        stage('Testing conjur_variable lookup plugin for GCP') {
          steps {
            script {
              INFRAPOOL_EXECUTORV2_AGENT_1.agentSh './ci/test.sh -u gcp -d -t conjur_variable'
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
              INFRAPOOL_EXECUTORV2_AGENT_1.agentUnstash name: 'token-out-cloud'
              INFRAPOOL_EXECUTORV2_AGENT_1.agentSh "./dev/start.sh -f edge -a gcp -v ${LATEST_ANSIBLE_VERSION} -p 3.13"
              INFRAPOOL_EXECUTORV2_AGENT_1.agentSh './ci/test.sh -u gcp -d -t conjur_variable'
            }
          }
        }
        stage('Get Edge Token for Azure') {
          steps {
            script {
              def edge_token = getConjurCloudTenant.tokens(
                      infrapool: INFRAPOOL_EXECUTORV2_AGENT_1,
                      conjur_url: "${TENANT.conjur_cloud_url}",
                      edge_name: "${TENANT.conjur_edge_name}",
                      conjur_token: "${conj_token}"
              )

              def deploy_edge = getConjurCloudTenant.edge(
                      infrapool:  INFRAPOOL_AZURE_EXECUTORV2_AGENT_1,
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
              INFRAPOOL_AZURE_EXECUTORV2_AGENT_1.agentSh"summon ./dev/start.sh -f cloud -a azure -v ${LATEST_ANSIBLE_VERSION} -p 3.13"
            }
          }
        }

        stage('Testing conjur_variable lookup plugin for Azure') {
          steps {
            script {
              INFRAPOOL_AZURE_EXECUTORV2_AGENT_1.agentSh 'summon ./ci/test.sh -u azure -d -t conjur_variable'
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
              INFRAPOOL_AZURE_EXECUTORV2_AGENT_1.agentSh "summon ./dev/start.sh -f edge -a azure -v ${LATEST_ANSIBLE_VERSION} -p 3.13"
              INFRAPOOL_AZURE_EXECUTORV2_AGENT_1.agentSh 'summon ./ci/test.sh -u azure -d -t conjur_variable'
            }
          }
        }
      }
    }
    stage('Build artifacts') {
      steps {
        script {
          INFRAPOOL_EXECUTORV2_AGENT_1.agentSh './ci/build_release'
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
          release(INFRAPOOL_EXECUTORV2_AGENT_1) { billOfMaterialsDirectory, assetDirectory, toolsDirectory ->
            // Publish release artifacts to all the appropriate locations
            // Copy any artifacts to assetDirectory to attach them to the Github release
            INFRAPOOL_EXECUTORV2_AGENT_1.agentSh "cp cyberark-conjur-*.tar.gz  ${assetDirectory}"
          }
        }
      }
    }
  }
  post {
    always {
      script {
        if (params.TEST_CLOUD) {
          deleteConjurCloudTenant("${TENANT.id}")
        }
      }
      releaseInfraPoolAgent(".infrapool/release_agents")
    }
  }
}

static def runApiKeyIntegrationTests(executorAgent, ansibleVersion, conjurFlavour, pythonVersion) {
  executorAgent.agentSh "./dev/start.sh -f ${conjurFlavour} -a api_key -v ${ansibleVersion} -p ${pythonVersion}"
  executorAgent.agentSh './ci/test.sh -u api_key -d -t conjur_variable'
  executorAgent.agentSh './ci/test.sh -d -t conjur_host_identity'
}

static def runIamIntegrationTests(executorAgent, ansibleVersion, conjurFlavour, pythonVersion) {
  executorAgent.agentSh "./dev/start.sh -f ${conjurFlavour} -a iam  -v ${ansibleVersion} -p ${pythonVersion}"
  executorAgent.agentSh './ci/test.sh -u iam -d -t conjur_variable'
}

static def runAzureIntegrationTests(azureExecutorAgent, ansibleVersion, conjurFlavour, pythonVersion) {
  azureExecutorAgent.agentSh "summon ./dev/start.sh -f ${conjurFlavour} -a azure -v ${ansibleVersion} -p ${pythonVersion}"
  azureExecutorAgent.agentSh 'summon ./ci/test.sh -u azure -d -t conjur_variable'
}

static def runGcpIntegrationTests(executorAgent, gcpExecutorAgent, ansibleVersion, conjurFlavour, pythonVersion, appName, stashName) {
  gcpExecutorAgent.agentSh "./dev/get_gcp_token.sh host/gcp-apps/test-app ${appName}"
  gcpExecutorAgent.agentStash name: stashName, includes: 'dev/gcp/*'
  executorAgent.agentUnstash name: stashName
  executorAgent.agentSh "./dev/start.sh -f ${conjurFlavour} -a gcp  -v ${ansibleVersion} -p ${pythonVersion}"
  executorAgent.agentSh './ci/test.sh -u gcp -d -t conjur_variable'
}

static def runAnsibleLint(executorAgent) {
  executorAgent.agentSh './dev/lint.sh'
}

static def runSanityTests(executorAgent, version, pythonVersion) {
  executorAgent.agentSh "./dev/test_sanity.sh -a ${version} -p ${pythonVersion}"
}

def runSanityTestsDefault(executorAgent) {
  executorAgent.agentSh './dev/test_sanity.sh -r'
  executorAgent.agentStash name: 'sanity-test-report', includes: 'tests/output/reports/coverage=sanity/*'
  unstash 'sanity-test-report'
}

def handleJunitReports(executorAgent, stashName, testFilesPattern) {
  executorAgent.agentStash name: stashName, includes: testFilesPattern
  unstash stashName
  junit testFilesPattern
}