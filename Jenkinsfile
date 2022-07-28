#!/usr/bin/env groovy

pipeline {
  agent { label 'executor-v2' }

  options {
    timestamps()
    buildDiscarder(logRotator(numToKeepStr: '30'))
  }

    // environment {
    //     ansible_version = "2.13.1"
    //   }

  stages {
    stage('Validate') {
      parallel {
        stage('Changelog') {
          steps { sh './ci/parse-changelog.sh' }
        }
      }
    }



    stage('Run Enterprise tests')
    {
      stages {
                stage("Test conjur_variable lookup plugin")
                {
                  when {
                      branch 'ansible_conditions'
                      }
                        steps
                        {
                          script {
                                  def ansible_versions = ['2.13.1', '2.12.0','2.11.0']
                                  for (int i = 0; i < ansible_versions.size(); ++i)
                                    {
                                      echo "testing ${ansible_versions[i]}"

                                    // ./ci/test.sh -a 2.11.0 -d conjur_variable

                                    sh './ci/test.sh -a ${ansible_versions[i]} -d conjur_variable'

                                    // echo " $(./ci/test.sh -a ${ansible_versions[i]} -d conjur_variable)"
                                    // ./ci/test.sh -a ${ansible_versions[i]} -d conjur_variable

                                    // string abc = "./ci/test.sh -a ${ansible_versions[i]} -d conjur_variable"
                                    // echo " $(abc) "
                                    }
                                }
                          }
                }
              }
         }


            // stage('Run Open Source tests') {
            //   parallel {
            //     stage("Test conjur_variable lookup plugin") {
            //       environment {
            //         ansible_version = "2.13.1"
            //       }
            //       steps {
            //         sh './ci/test.sh -a 2.13.1 -d conjur_variable'
            //         // junit 'tests/conjur_variable/junit/*'
            //       }
            //     }

            //   }
            // }

    // stage('Run Enterprise tests') {
    //   stages {
    //     stage("Test conjur_variable lookup plugin") {
    //       steps {
    //         sh './ci/test.sh -e -d conjur_variable'
    //         junit 'tests/conjur_variable/junit/*'
    //       }
    //     }

    //   }
    // }


                                                                            //                             stage('Run Open Source tests') {

                                                                            //                           script {
                                                                            //                               def ansible_versions = ['2.13.1', '2.12.0','2.11.0']
                                                                            //                               for (int i = 0; i < ansible_versions.size(); ++i)
                                                                            //                                 {

                                                                            //                               parallel {
                                                                            //                                 stage("Test conjur_variable lookup plugin") {
                                                                            //                                   steps {
                                                                            //                                     sh './ci/test.sh -d conjur_variable'
                                                                            //                                     junit 'tests/conjur_variable/junit/*'
                                                                            //                                   }
                                                                            //                                 }

                                                                            //                                 // stage("Test conjur_host_identity role") {
                                                                            //                                 //   steps {
                                                                            //                                 //     sh './ci/test.sh -d conjur_host_identity'
                                                                            //                                 //     junit 'roles/conjur_host_identity/tests/junit/*'
                                                                            //                                 //   }
                                                                            //                                 // }

                                                                            //                                 stage("Run conjur_variable unit tests") {
                                                                            //                                   steps {
                                                                            //                                     sh './dev/test_unit.sh -r'
                                                                            //                                     publishHTML (target : [allowMissing: false,
                                                                            //                                       alwaysLinkToLastBuild: false,
                                                                            //                                       keepAll: true,
                                                                            //                                       reportDir: 'tests/output/reports/coverage=units/',
                                                                            //                                       reportFiles: 'index.html',
                                                                            //                                       reportName: 'Ansible Coverage Report',
                                                                            //                                       reportTitles: 'Conjur Ansible Collection report'])
                                                                            //                                   }
                                                                            //                                 }
                                                                            //                               }
                                                                            //                                 }
                                                                            //                           }

                                                                            //                             }

                                                                            // stage('Run Enterprise tests') {
                                                                            //   stages {
                                                                            //     stage("Test conjur_variable lookup plugin") {
                                                                            //       steps {
                                                                            //         sh './ci/test.sh -e -d conjur_variable'
                                                                            //         junit 'tests/conjur_variable/junit/*'
                                                                            //       }
                                                                            //     }

                                                                            //     // stage("Test conjur_host_identity role") {
                                                                            //     //   steps {
                                                                            //     //     sh './ci/test.sh -e -d conjur_host_identity'
                                                                            //     //     junit 'roles/conjur_host_identity/tests/junit/*'
                                                                            //     //   }
                                                                            //     // }
                                                                            //   }
                                                                            // }


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