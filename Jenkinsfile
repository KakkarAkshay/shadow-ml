pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    environment {
        AWS_REGION    = 'ap-southeast-2'
        ECR_REPO      = 'shadow-ml'
        IMAGE_TAG     = "${env.BUILD_NUMBER}"
        APP_SERVER_IP = '172.31.3.160'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Install') {
            steps {
                sh '''
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install --no-cache-dir -r requirements.txt
                '''
            }
        }

        stage('Test') {
            steps {
                sh '''
                    . .venv/bin/activate
                    python -m pytest
                '''
            }
        }

        stage('Build') {
            steps {
                sh '''
                    . .venv/bin/activate
                    python -m compileall -q app ml
                '''
            }
        }

        stage('Docker Build') {
            steps {
                sh 'docker build -t ${ECR_REPO}:${IMAGE_TAG} .'
            }
        }

        stage('Docker Push') {
            steps {
                sh '''
                    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
                    REGISTRY="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
                    aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${REGISTRY}
                    docker tag ${ECR_REPO}:${IMAGE_TAG} ${REGISTRY}/${ECR_REPO}:${IMAGE_TAG}
                    docker tag ${ECR_REPO}:${IMAGE_TAG} ${REGISTRY}/${ECR_REPO}:latest
                    docker push ${REGISTRY}/${ECR_REPO}:${IMAGE_TAG}
                    docker push ${REGISTRY}/${ECR_REPO}:latest
                '''
            }
        }

        stage('Deploy') {
            steps {
                sshagent(credentials: ['app-server-ssh']) {
                    sh '''
                        ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
                        REGISTRY="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
                        REMOTE="ssh -o StrictHostKeyChecking=accept-new ubuntu@${APP_SERVER_IP}"
                        aws ecr get-login-password --region ${AWS_REGION} | $REMOTE "docker login --username AWS --password-stdin ${REGISTRY}"
                        scp -o StrictHostKeyChecking=accept-new deploy/deploy.sh ubuntu@${APP_SERVER_IP}:/tmp/deploy.sh
                        $REMOTE "bash /tmp/deploy.sh ${REGISTRY}/${ECR_REPO}:${IMAGE_TAG} ${IMAGE_TAG}"
                    '''
                }
            }
        }
    }

    post {
        always {
            sh 'docker image prune -f || true'
        }
    }
}
