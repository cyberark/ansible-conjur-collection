#!/usr/bin/env groovy

pipeline {
  agent { label 'executor-v2' }

  options {
    timestamps()
    buildDiscarder(logRotator(numToKeepStr: '30'))
  }

  stage('Validate') {
    parallel {
      stage('Changelog') {
        steps { sh './bin/parse-changelog.sh' }
      }
    }
  }

  stages {
    stage('Run tests') {
      steps {
        sh './bin/test.sh'
        junit 'tests/junit/*'
      }
    }
  }

  post {
    always {
      cleanupAndNotify(currentBuild.currentResult)
    }
  }
}
