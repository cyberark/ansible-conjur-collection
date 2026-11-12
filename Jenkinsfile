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
    artifactoryAuth.withCreds(infrapool, "reader") {
      def hostRef = artifactoryAuth.hostVarRef(infrapool)
      def userRef = artifactoryAuth.userVarRef(infrapool)
      def passRef = artifactoryAuth.passVarRef(infrapool)
      infrapool.agentSh """
        set -e
        install -m 600 /dev/null pip.conf
        printf \"[global]\\nindex-url = https://%s:%s@%s/artifactory/api/pypi/everest-pypi-virtual/simple\\n\" \\
          "${userRef}" "${passRef}" "${hostRef}" > pip.conf

        ls "${assetDirectory}"
        cp "${assetDirectory}/cyberark-conjur-${targetVersion}.tar.gz" ./cyberark-conjur-${targetVersion}.tar.gz

        export TAG="v${targetVersion}"
        CI_REQUIRE_ARTIFACTORY=true summon -e publish ./ci/publish
        rm -f pip.conf
      """
    }
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
    ANSIBLE_VERSION = '2.19'
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

    // Writes the repo-root pip.conf that every pip install in the build uses
    stage('Prepare pip.conf') {
      steps {
        script {
          writeArtifactoryPipConf(INFRAPOOL_EXECUTORV2_AGENT_1)
          writeArtifactoryPipConf(INFRAPOOL_EXECUTORV2_AGENT_2)
          // Azure agents never run pip install (image is pre-built on AWS and relayed).
          // Use the public pip.conf template — no Artifactory credentials needed or distributed.
          INFRAPOOL_AZURE_EXECUTORV2_AGENT_1.agentSh 'install -m 600 pip.conf.dist pip.conf'
          INFRAPOOL_AZURE_EXECUTORV2_AGENT_2.agentSh 'install -m 600 pip.conf.dist pip.conf'
        }
      }
    }

    // Refreshes Ansible Automation Hub token to prevent 30-day inactivity expiration
    stage('Refresh Automation Hub Token') {
      steps {
        script {
              INFRAPOOL_EXECUTORV2_AGENT_1.agentSh 'summon -e publish ./ci/token_refresh.sh'
            }
          }
        }

    stage('Build artifacts') {
      steps {
        script {
          INFRAPOOL_EXECUTORV2_AGENT_1.agentSh './ci/build_release'
          INFRAPOOL_EXECUTORV2_AGENT_1.agentArchiveArtifacts artifacts: 'cyberark-conjur-*.tar.gz', fingerprint: true
          // Stash so Azure agents can reuse this artifact instead of rebuilding it.
          INFRAPOOL_EXECUTORV2_AGENT_1.agentStash name: 'collection-artifact', includes: 'cyberark-conjur-*.tar.gz'
        }
      }
    }

    stage('Verify requirements.txt files are up to date') {
      steps {
        script {
          INFRAPOOL_EXECUTORV2_AGENT_1.agentSh """
              set -e
              ./dev/compile_requirements.sh
              git diff --exit-code \\
                tests/unit/requirements.txt \\
                dev/oidc-provider/requirements.txt \\
                tests/requirements-ansible-core-2.17.txt \\
                tests/requirements-ansible-core-2.18.txt \\
                tests/requirements-ansible-core-2.19.txt \\
                dev/requirements-ansible-11.txt \\
                dev/requirements-ansible-12.txt \\
                ci/requirements-build.txt \\
                ci/requirements-publish.txt || \\
                (echo "One or more requirements.txt files are out of date — run ./dev/compile_requirements.sh to regenerate" && exit 1)
          """
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
          recordCoverage(
            tools: [[parser: 'COBERTURA', pattern: 'tests/output/reports/coverage=units.xml']],
            sourceCodeEncoding: 'ASCII',
            qualityGates: [
              [threshold: 30.0, metric: 'LINE',   baseline: 'PROJECT', unstable: true],
              [threshold: 30.0, metric: 'BRANCH', baseline: 'PROJECT', unstable: true],
              [threshold: 30.0, metric: 'METHOD', baseline: 'PROJECT', unstable: true]
            ]
          )
          codacy action: 'reportCoverage', filePath: "tests/output/reports/coverage=units.xml"
        }
      }
    }

    stage('Run conjur_variable sanity tests') {
      parallel {
        stage ('Run ansible-lint') {
          steps {
            script {
              INFRAPOOL_EXECUTORV2_AGENT_1.agentSh './dev/lint.sh'
            }
          }
        }

        stage('conjur_variable sanity tests for Ansible core 2.17') {
          steps {
            script {
              INFRAPOOL_EXECUTORV2_AGENT_1.agentSh './dev/test_sanity.sh -a 2.17 -p 3.12'
            }
          }
        }

        stage('conjur_variable sanity tests for Ansible core 2.18') {
          steps {
            script {
              INFRAPOOL_EXECUTORV2_AGENT_1.agentSh './dev/test_sanity.sh -a 2.18 -p 3.13'
            }
          }
        }

        stage('conjur_variable sanity tests for Ansible core (2.19) - default') {
          steps {
            script {
              INFRAPOOL_EXECUTORV2_AGENT_1.agentSh './dev/test_sanity.sh -r'
              INFRAPOOL_EXECUTORV2_AGENT_1.agentStash name: 'sanity-test-report', includes: 'tests/output/reports/coverage=sanity/*'
              unstash 'sanity-test-report'
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
            script {
              parallel(
                "Ansible 11": {
                  runApiKeyIntegrationTests(INFRAPOOL_EXECUTORV2_AGENT_1, '11', 'oss', '3.12')
                },
                "Ansible 12": {
                  runApiKeyIntegrationTests(INFRAPOOL_EXECUTORV2_AGENT_2, LATEST_ANSIBLE_VERSION, 'oss', '3.12')
                }
              )
            }
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
            script {
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
    }

    stage('IAM Integration Tests') {
      stages {
        stage('Run IAM Integration Tests with Conjur OSS') {
          steps {
            script {
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
        }

        stage('Run IAM Integration Tests with Conjur Enterprise') {
          steps {
            script {
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
    }
    stage('Authn Cert Integration Tests') {
      stages {
        // authn-cert for Conjur Open Source has not yet been shipped in the public cyberark/conjur Docker image
        // (latest: v1.24.0, released Nov 2025). The public OSS repo (cyberark/conjur) has no authn-cert route
        // Until a new OSS image is published with authn-cert support, tests can only run against Enterprise.

//         stage('Run Authn Cert Integration Tests with Conjur OSS') {
//           steps {
//             parallel(
//                     "Ansible 11": {
//                       runAuthnCertIntegrationTests(INFRAPOOL_EXECUTORV2_AGENT_1, '11', 'oss', '3.12')
//                     },
//                     "Ansible 12": {
//                       runAuthnCertIntegrationTests(INFRAPOOL_EXECUTORV2_AGENT_2, LATEST_ANSIBLE_VERSION, 'oss', '3.12')
//                     }
//             )
//           }
//         }

        stage('Run Authn Cert Integration Tests with Conjur Enterprise') {
          steps {
            script {
              parallel(
                "Ansible 11": {
                  runAuthnCertIntegrationTests(INFRAPOOL_EXECUTORV2_AGENT_1, '11', 'enterprise', '3.12')
                },
                "Ansible 12": {
                  runAuthnCertIntegrationTests(INFRAPOOL_EXECUTORV2_AGENT_2, LATEST_ANSIBLE_VERSION, 'enterprise', '3.12')
                }
              )
            }
          }
        }
      }
    }

    stage('JWT Integration Tests') {
      stages {
        stage('Run JWT Integration Tests with Conjur OSS') {
          steps {
            script {
              parallel(
                "Ansible 11": {
                  runJwtOidcIntegrationTests(INFRAPOOL_EXECUTORV2_AGENT_1, '11', 'oss', '3.12')
                },
                "Ansible 12": {
                  runJwtOidcIntegrationTests(INFRAPOOL_EXECUTORV2_AGENT_2, LATEST_ANSIBLE_VERSION, 'oss', '3.12')
                }
              )
            }
          }
        }

        stage('Run JWT Integration Tests with Conjur Enterprise') {
          steps {
            script {
              parallel(
                "Ansible 11": {
                  runJwtOidcIntegrationTests(INFRAPOOL_EXECUTORV2_AGENT_1, '11', 'enterprise', '3.12')
                },
                "Ansible 12": {
                  runJwtOidcIntegrationTests(INFRAPOOL_EXECUTORV2_AGENT_2, LATEST_ANSIBLE_VERSION, 'enterprise', '3.12')
                }
              )
            }
          }
        }
      }
    }

    stage('Build Ansible test images for Azure') {
      steps {
        script {
          // Build on the AWS agent, which has Artifactory access via pip.conf.
          buildAnsibleTestImage(INFRAPOOL_EXECUTORV2_AGENT_1, '11', '3.12')
          buildAnsibleTestImage(INFRAPOOL_EXECUTORV2_AGENT_1, LATEST_ANSIBLE_VERSION, '3.12')
          if (params.TEST_CLOUD) {
            buildAnsibleTestImage(INFRAPOOL_EXECUTORV2_AGENT_1, LATEST_ANSIBLE_VERSION, '3.13')
          }
        }
      }
    }

    stage('Azure Integration Tests') {
      stages {
        stage('Run Azure Integration Tests with Conjur OSS') {
          steps {
            script {
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
        }

        stage('Run Azure Integration Tests with Conjur Enterprise') {
          steps {
            script {
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
    }

    stage('GCP Integration Tests') {
      stages {
        stage('Run GCP Integration Tests with Conjur OSS') {
          steps {
            script {
              // Only the executor agents run start.sh (docker-compose); GCP agents only fetch tokens
              parallel(
                "Ansible 11": {
                  runGcpIntegrationTests(
                    INFRAPOOL_EXECUTORV2_AGENT_1, INFRAPOOL_GCP_EXECUTORV2_AGENT_1,
                    '11', 'oss', '3.12', 'cucumber', 'token-out'
                  )
                },
                "Ansible 12": {
                  runGcpIntegrationTests(
                    INFRAPOOL_EXECUTORV2_AGENT_2, INFRAPOOL_GCP_EXECUTORV2_AGENT_2,
                    LATEST_ANSIBLE_VERSION, 'oss', '3.12', 'cucumber', 'token-out'
                  )
                }
              )
            }
          }
        }

        stage('Run GCP Integration Tests with Conjur Enterprise') {
          steps {
            script {
              parallel(
                "Ansible 11": {
                  runGcpIntegrationTests(
                    INFRAPOOL_EXECUTORV2_AGENT_1, INFRAPOOL_GCP_EXECUTORV2_AGENT_1,
                    '11', 'enterprise', '3.12', 'demo', 'token-out-enterprise'
                  )
                },
                "Ansible 12": {
                  runGcpIntegrationTests(
                    INFRAPOOL_EXECUTORV2_AGENT_2, INFRAPOOL_GCP_EXECUTORV2_AGENT_2,
                    LATEST_ANSIBLE_VERSION, 'enterprise', '3.12', 'demo', 'token-out-enterprise'
                  )
                }
              )
            }
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
              // NOTE: These two stages must run sequentially, not in parallel.
              // They share the same InfraPool agent/workspace and the same
              // docker-compose project ("dev"), including the same "ansible"
              // container. Running them concurrently lets one stage's
              // docker-compose operations interfere with the other's containers,
              // causing flaky failures (e.g. retrieve-variable-into-file losing
              // its /dev/shm secret file).
              stages {
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
              def tag = ansibleTestImage(LATEST_ANSIBLE_VERSION, '3.13')
              // Relay the pre-built image from the AWS agent — Azure agents cannot reach Artifactory.
              relayAnsibleTestImage(INFRAPOOL_EXECUTORV2_AGENT_1, INFRAPOOL_AZURE_EXECUTORV2_AGENT_1, tag)
              // CI_REQUIRE_ARTIFACTORY=false: Azure agents carry the public pip.conf template (PyPI URL).
              INFRAPOOL_AZURE_EXECUTORV2_AGENT_1.agentSh "CI_REQUIRE_ARTIFACTORY=false ANSIBLE_IMAGE=${tag} summon -e azure ./dev/start.sh -f cloud -a azure -v ${LATEST_ANSIBLE_VERSION} -p 3.13"
            }
          }
        }

        stage('Testing conjur_variable lookup plugin for Azure') {
          steps {
            script {
              INFRAPOOL_AZURE_EXECUTORV2_AGENT_1.agentSh 'summon -e azure ./ci/test.sh -u azure -d -t conjur_variable'
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
              // Image already relayed to Azure agent 1 in 'Run Azure tests against Cloud Tenant'.
              def tag = ansibleTestImage(LATEST_ANSIBLE_VERSION, '3.13')
              INFRAPOOL_AZURE_EXECUTORV2_AGENT_1.agentSh "CI_REQUIRE_ARTIFACTORY=false ANSIBLE_IMAGE=${tag} summon -e azure ./dev/start.sh -f edge -a azure -v ${LATEST_ANSIBLE_VERSION} -p 3.13"
              INFRAPOOL_AZURE_EXECUTORV2_AGENT_1.agentSh 'summon -e azure ./ci/test.sh -u azure -d -t conjur_variable'
            }
          }
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
        removePipConf { INFRAPOOL_EXECUTORV2_AGENT_1 }
        removePipConf { INFRAPOOL_EXECUTORV2_AGENT_2 }
        removePipConf { INFRAPOOL_AZURE_EXECUTORV2_AGENT_1 }
        removePipConf { INFRAPOOL_AZURE_EXECUTORV2_AGENT_2 }
      }
      releaseInfraPoolAgent(".infrapool/release_agents")
    }
  }
}

// Writes the Artifactory pip.conf directly into the agent's workspace root (repo root).
// Credentials are expanded by the shell on the agent (never Groovy-interpolated);
// the file is created with mode 600 before credentials are written.
def writeArtifactoryPipConf(agent) {
  artifactoryAuth.withCreds(agent, "reader") {
    def hostRef = artifactoryAuth.hostVarRef(agent)
    def userRef = artifactoryAuth.userVarRef(agent)
    def passRef = artifactoryAuth.passVarRef(agent)
    agent.agentSh """
      install -m 600 /dev/null pip.conf
      printf '[global]\\nindex-url = https://%s:%s@%s/artifactory/api/pypi/everest-pypi-virtual/simple\\n' \\
        "${userRef}" "${passRef}" "${hostRef}" > pip.conf
    """
  }
}

// Removes pip.conf from an agent; the agent may not exist if leasing failed.
def removePipConf(Closure getAgent) {
  try {
    getAgent().agentSh 'rm -f pip.conf dev/tmp/pip.conf'
  } catch (e) {
    echo "Skipping pip.conf cleanup: ${e.message}"
  }
}

def runApiKeyIntegrationTests(executorAgent, ansibleVersion, conjurFlavour, pythonVersion) {
  executorAgent.agentSh "./dev/start.sh -f ${conjurFlavour} -a api_key -v ${ansibleVersion} -p ${pythonVersion}"
  executorAgent.agentSh './ci/test.sh -u api_key -d -t conjur_variable'
  executorAgent.agentSh './ci/test.sh -d -t conjur_host_identity'
}

def runIamIntegrationTests(executorAgent, ansibleVersion, conjurFlavour, pythonVersion) {
  executorAgent.agentSh "./dev/start.sh -f ${conjurFlavour} -a iam -v ${ansibleVersion} -p ${pythonVersion}"
  executorAgent.agentSh './ci/test.sh -u iam -d -t conjur_variable'
}

def runAuthnCertIntegrationTests(executorAgent, ansibleVersion, conjurFlavour, pythonVersion) {
  executorAgent.agentSh "./dev/start.sh -f ${conjurFlavour} -a authn-cert -v ${ansibleVersion} -p ${pythonVersion}"
  executorAgent.agentSh './ci/test.sh -u authn-cert -d -t conjur_variable'
}

def runJwtOidcIntegrationTests(executorAgent, ansibleVersion, conjurFlavour, pythonVersion) {
  executorAgent.agentSh "./dev/start.sh -f ${conjurFlavour} -a jwt-oidc -v ${ansibleVersion} -p ${pythonVersion}"
  executorAgent.agentSh './ci/test.sh -u jwt-oidc -d -t conjur_variable'
}

// Returns the Docker image tag for the Ansible test image for the given Ansible and Python versions.
// The tag includes a short git commit hash so reused Azure VMs cannot pick up a stale image
// from a different branch that happened to share the same BUILD_NUMBER.
def ansibleTestImage(String ansibleVersion, String pythonVersion) {
  def shortCommit = env.GIT_COMMIT?.take(12) ?: 'local'
  return "ansible-conjur-test:${shortCommit}-${BUILD_NUMBER}-a${ansibleVersion}-py${pythonVersion}"
}

// Builds the Ansible test image on the given agent using the repo-root pip.conf secret.
// Returns the image tag.
def buildAnsibleTestImage(agent, String ansibleVersion, String pythonVersion) {
  def tag = ansibleTestImage(ansibleVersion, pythonVersion)
  // BuildKit refuses --secret src paths outside the build context (dev/), so copy into dev/tmp/.
  agent.agentSh """
    mkdir -p dev/tmp
    cp cyberark-conjur-*.tar.gz dev/
    trap 'rm -f dev/tmp/pip.conf dev/cyberark-conjur-*.tar.gz' EXIT
    install -m 600 pip.conf dev/tmp/pip.conf
    DOCKER_BUILDKIT=1 docker build \\
      --secret id=pip_conf,src=dev/tmp/pip.conf \\
      --build-arg ANSIBLE_VERSION=${ansibleVersion} \\
      --build-arg PYTHON_VERSION=${pythonVersion} \\
      -t ${tag} dev/
  """
  return tag
}

// Relays the named image from one InfraPool agent to another via dockerRelayImage.
def relayAnsibleTestImage(fromAgent, toAgent, String tag) {
  dockerRelayImage(fromAgent, toAgent, [tag])
}

def runAzureIntegrationTests(azureExecutorAgent, ansibleVersion, conjurFlavour, pythonVersion) {
  azureExecutorAgent.agentUnstash name: 'collection-artifact'
  def tag = ansibleTestImage(ansibleVersion, pythonVersion)
  // Relay the pre-built image from the AWS agent — Azure agents cannot reach Artifactory.
  relayAnsibleTestImage(INFRAPOOL_EXECUTORV2_AGENT_1, azureExecutorAgent, tag)
  // CI_REQUIRE_ARTIFACTORY=false: Azure agents carry the public pip.conf template (PyPI URL).
  azureExecutorAgent.agentSh "CI_REQUIRE_ARTIFACTORY=false ANSIBLE_IMAGE=${tag} summon -e azure ./dev/start.sh -f ${conjurFlavour} -a azure -v ${ansibleVersion} -p ${pythonVersion}"
  azureExecutorAgent.agentSh 'summon -e azure ./ci/test.sh -u azure -d -t conjur_variable'
}

def runGcpIntegrationTests(executorAgent, gcpExecutorAgent, ansibleVersion, conjurFlavour, pythonVersion, appName, stashName) {
  gcpExecutorAgent.agentSh "./dev/get_gcp_token.sh host/gcp-apps/test-app ${appName}"
  gcpExecutorAgent.agentStash name: stashName, includes: 'dev/gcp/*'
  executorAgent.agentUnstash name: stashName
  executorAgent.agentSh "./dev/start.sh -f ${conjurFlavour} -a gcp -v ${ansibleVersion} -p ${pythonVersion}"
  executorAgent.agentSh './ci/test.sh -u gcp -d -t conjur_variable'
}

def handleJunitReports(executorAgent, stashName, testFilesPattern) {
  executorAgent.agentStash name: stashName, includes: testFilesPattern
  unstash stashName
  junit testFilesPattern
}
