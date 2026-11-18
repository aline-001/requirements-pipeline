// CI/CD for the Requirements Engineering Pipeline.
// Runs on every new commit on main: StrictDoc check -> RTM build -> publish to rtm.darho.rw
pipeline {
  agent { docker { image 'python:3.12' } }

  environment {
    HOME = "${WORKSPACE}"
    PIP_CACHE_DIR = "${WORKSPACE}/.pip-cache"
  }

  options {
    timestamps()
    timeout(time: 20, unit: 'MINUTES')
    buildDiscarder(logRotator(numToKeepStr: '30'))
    disableConcurrentBuilds()
  }

  triggers { pollSCM('H/15 * * * *') }   // checks GitHub every 15 minutes

  stages {
    stage('Set up tools') {
      steps {
        sh '''
          python3 -m venv .venv
          .venv/bin/pip install -q strictdoc==0.30.4 requests
        '''
      }
    }

    stage('StrictDoc check') {
      steps {
        sh '''
          .venv/bin/strictdoc export . --output-dir build/strictdoc > strictdoc.log 2>&1 \
            || { echo "StrictDoc rejected the files:"; tail -30 strictdoc.log; exit 1; }
        '''
      }
    }

    stage('Build RTM') {
      steps {
        sh '''
          rm -rf build/site && mkdir -p build/site
          .venv/bin/python rtm.py --out build/site
          cp -r build/strictdoc/html build/site/strictdoc
          cat build/site/coverage.txt || true
        '''
      }
    }

    stage('Publish') {
      steps {
        sh '''
          rm -rf /srv/rtm-site/next /srv/rtm-site/old
          cp -r build/site /srv/rtm-site/next
          [ -d /srv/rtm-site/current ] && mv /srv/rtm-site/current /srv/rtm-site/old
          mv /srv/rtm-site/next /srv/rtm-site/current
          rm -rf /srv/rtm-site/old
          echo "Published commit $(git rev-parse --short HEAD) to https://rtm.darho.rw"
        '''
      }
    }
  }

  post {
    success { archiveArtifacts artifacts: 'build/site/rtm.csv, build/site/coverage.txt', allowEmptyArchive: true }
    failure { echo 'Build failed: see the stage marked red above.' }
  }
}
