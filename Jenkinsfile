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

    // stage('Run tests') {
    //   parallel {
    //     stage("Test conjur_variable lookup plugin") {
    //       steps {
    //         sh './ci/test.sh -d conjur_variable'
    //         junit 'tests/conjur_variable/junit/*'
    //       }
    //     }

    //     stage("Test conjur_host_identity role") {
    //       steps {
    //         sh './ci/test.sh -d conjur_host_identity'
    //         junit 'roles/conjur_host_identity/tests/junit/*'
    //       }
    //     }

    //     stage("Run conjur_variable unit tests") {
    //       steps {
    //         sh './dev/test_unit.sh -r'
    //         publishHTML (target : [allowMissing: false,
    //           alwaysLinkToLastBuild: false,
    //           keepAll: true,
    //           reportDir: 'tests/output/reports/coverage=units/',
    //           reportFiles: 'index.html',
    //           reportName: 'Ansible Coverage Report',
    //           reportTitles: 'Conjur Ansible Collection report'])
    //       }
    //     }
    //   }
    // }

    // stage('Run tests against Conjur Enterprise') {
    //   steps {
    //     sh './ci/test.sh -e -d conjur_variable'
    //   }
    // }

    // stage('Run tests against Conjur Enterprise') {
    //   steps {
    //     sh './testing_role.sh'
    //   }
    // }

    // stage('Run tests against Conjur Enterprise') {
    //   steps {
    //     sh './tests/conjur_variable/test.sh'
    //   }
    // }

    stage('Run tests against Conjur Enterprise') {
      steps {
        sh './roles/conjur_host_identity/tests/role_test.sh'
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
