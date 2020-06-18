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
          steps { sh './bin/parse-changelog.sh' }
        }
      }
    }

    stage('Run tests') {
      steps {
        sh './bin/test.sh'
        junit 'tests/junit/*'
      }
    }

    stage('Build Release Artifacts') {
      when {
        branch 'master'
      }

      steps {
        sh './bin/build_release'
        archiveArtifacts 'cyberark-conjur-*.tar.gz'
      }
    }
  }

  post {
    always {
      cleanupAndNotify(currentBuild.currentResult)
    }
  }
}
