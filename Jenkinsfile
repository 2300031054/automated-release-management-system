pipeline {
    agent any

    environment {
        APP_NAME = 'automated-release-app'
        IMAGE_TAG = "${env.BUILD_NUMBER}"
        DOCKER_USER = '2300031054'
    }

    stages {
        stage('1. Checkout Code') {
            steps { checkout scm }
        }

        stage('2. Run Automated Unit Tests') {
            steps {
                sh '''
                    python3 -m venv venv || true
                    . venv/bin/activate || true
                    pip install -r requirements.txt
                    PYTHONPATH=app pytest app/test_main.py
                '''
            }
        }

        stage('3. Build Docker Image') {
            steps {
                sh "docker build -t ${DOCKER_USER}/${APP_NAME}:${IMAGE_TAG} ."
            }
        }

        stage('4. Deploy Application') {
            steps {
                sh 'docker-compose down || true'
                sh 'docker-compose up -d --build'
            }
        }
    }

    post {
        success { echo '🎉 Pipeline Succeeded! Software released.' }
        failure { echo '❌ Pipeline Failed!' }
    }
}
