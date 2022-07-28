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



    stage('Run Enterprise tests') {
            when {
            branch ‘ansible_conditions’
            }
      stages {
        stage("Test conjur_variable lookup plugin") {
          steps {
                    script {
                    def ansibleversions = ['2.13.1', '2.12.0','2.11.0']
                    for (int i = 0; i < 2; ++i)
                             {
                               sh ' echo testing ${ansibleversions[i]}'
                    //  sh './ci/test.sh -a ${ansibleversions[i]} -d conjur_variable'
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