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
          steps { parseChangelog() }
        }
      }
    }

    stage('Run integration tests with Conjur Enterprise') {
      stages {
        stage("Testing conjur_variable lookup plugin") {
          steps {
            sh './ci/test.sh -e -d conjur_variable'
            junit 'tests/conjur_variable/junit/*'
          }
        }

        stage("Testing conjur_host_identity role") {
          steps {
            sh './ci/test.sh -e -d conjur_host_identity'
            junit 'roles/conjur_host_identity/tests/junit/*'
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
      cleanupAndNotify(currentBuild.currentResult)
    }
  }
}