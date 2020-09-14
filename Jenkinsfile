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
        stage("Test Ansible-Conjur-Collection") {
          agent { label 'executor-v2-large' }

          steps {
            sh './ci/test.sh -d conjur'
            junit 'tests/conjur/junit/*'
          }
        }

        stage("Test Ansible-Conjur-Host-Identity") {
          steps {
            sh './ci/test.sh -d conjur-host-identity'
            junit 'tests/conjur-host-identity/junit/*'
          }
        }
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
