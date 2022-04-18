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

    stage('Run tests') {
      parallel {
        stage("Test conjur_variable lookup plugin") {
          steps {
            sh './ci/test.sh -d conjur_variable'
            junit 'tests/conjur_variable/junit/*'
          }
        }

        stage("Test conjur_host_identity role") {
          steps {
            sh './ci/test.sh -d conjur_host_identity'
            junit 'roles/conjur_host_identity/tests/junit/*'
            sh 'chmod +x ./tests/ansibletest.sh'
          }
        }
      }
    }
//     stage('Report Test Code Coverage'){
//           steps {
//             publishHTML (target : [allowMissing: false,
//             alwaysLinkToLastBuild: false,
//             keepAll: true,
//             reportDir: 'tests/output/reports/coverage=units=python-3.8/',
//             reportFiles: 'index.html',
//             reportName: 'Ansible Coverage Report',
//             reportTitles: 'Conjur Ansible Collection report'])
//            }
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
