pipeline {
    agent any

    environment {
        AWS_DEFAULT_REGION    = 'ap-south-1'
        ECR_REPO              = '227769753445.dkr.ecr.ap-south-1.amazonaws.com/ema-backtester'
        IMAGE_TAG             = "${env.GIT_COMMIT ? env.GIT_COMMIT.take(7) : 'latest'}"
        AWS_ACCESS_KEY_ID     = credentials('AWS_ACCESS_KEY_ID')
        AWS_SECRET_ACCESS_KEY = credentials('AWS_SECRET_ACCESS_KEY')
    }

    stages {
        stage('Install Dependencies') {
            steps {
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                '''
            }
        }

        stage('Run Tests') {
            steps {
                sh '''
                    . venv/bin/activate
                    pytest test_backtester.py -v
                '''
            }
        }

        stage('Trivy Filesystem Scan') {
            steps {
                sh '''
                    trivy fs --severity HIGH,CRITICAL --exit-code 0 --format table .
                '''
            }
        }

        stage('Build Docker Image') {
            steps {
                sh '''
                    docker build -t ${ECR_REPO}:${IMAGE_TAG} -t ${ECR_REPO}:latest .
                '''
            }
        }

        stage('Push to ECR') {
            steps {
                sh '''
                    aws ecr get-login-password --region ${AWS_DEFAULT_REGION} | docker login --username AWS --password-stdin ${ECR_REPO}
                    docker push ${ECR_REPO}:${IMAGE_TAG}
                    docker push ${ECR_REPO}:latest
                '''
            }
        }
    }

    post {
        success {
            echo "Pipeline succeeded. Image pushed: ${ECR_REPO}:${IMAGE_TAG}"
        }
        failure {
            echo "Pipeline failed, check stage logs above."
        }
        always {
            sh 'docker logout ${ECR_REPO} || true'
        }
    }
}