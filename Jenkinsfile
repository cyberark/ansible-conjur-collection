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

    stage('Run Open Source tests') {
      parallel {

        stage("Test conjur_variable lookup plugin") {
          when{
            branch 'ansible_conditions'
            }
          steps {
            sh 'echo TCS Noida'
            sh 'pip install https://github.com/ansible/ansible/archive/stable-2.10.tar.gz --disable-pip-version-check'
            sh 'ansible-test sanity --docker -v --color --python 3.9'
            sh './dev/test_unit.sh -a stable-2.10 -p 3.9'
            sh 'echo TCS Noida testing'
          }
        }

        // stage("Test conjur_variable lookup plugin") {
        //   steps {
        //     sh './ci/test.sh -d conjur_variable'
        //     junit 'tests/conjur_variable/junit/*'
        //   }
        // }

        // stage("Test conjur_host_identity role") {
        //   steps {
        //     sh './ci/test.sh -d conjur_host_identity'
        //     junit 'roles/conjur_host_identity/tests/junit/*'
        //   }
        // }

        // stage("Run conjur_variable unit tests") {
        //   steps {
        //     sh './dev/test_unit.sh -r'
        //     publishHTML (target : [allowMissing: false,
        //       alwaysLinkToLastBuild: false,
        //       keepAll: true,
        //       reportDir: 'tests/output/reports/coverage=units/',
        //       reportFiles: 'index.html',
        //       reportName: 'Ansible Coverage Report',
        //       reportTitles: 'Conjur Ansible Collection report'])
        //   }
        // }
      }
    }



    // stage('Run Enterprise tests') {
    //   stages {
    //     stage("Test conjur_variable lookup plugin") {
    //       steps {
    //         sh './ci/test.sh -e -d conjur_variable'
    //         junit 'tests/conjur_variable/junit/*'
    //       }
    //     }

    //     stage("Test conjur_host_identity role") {
    //       steps {
    //         sh './ci/test.sh -e -d conjur_host_identity'
    //         junit 'roles/conjur_host_identity/tests/junit/*'
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
