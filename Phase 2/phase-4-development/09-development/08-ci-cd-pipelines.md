# CI/CD Pipelines

This guide covers CI/CD pipelines for Jetson development projects.

## GitHub Actions

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.12'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest
    
    - name: Run tests
      run: pytest
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3

  build:
    runs-on: ubuntu-latest
    needs: test
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Build Docker image
      run: docker build -t myapp:${{ github.sha }} .
    
    - name: Run container
      run: |
        docker run -d myapp:${{ github.sha }}
        sleep 10
        docker logs myapp

  lint:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
    - name: Run flake8
      run: |
        pip install flake8
        flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
```

## GitLab CI

```yaml
# .gitlab-ci.yml
stages:
  - test
  - build
  - deploy

test:
  stage: test
  image: python:3.12
  script:
    - pip install -r requirements.txt
    - pytest
  only:
    - merge_requests
    - main

build:
  stage: build
  image: docker:latest
  services:
    - docker:dind
  script:
    - docker build -t myapp:$CI_COMMIT_SHA .
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
    - docker push myapp:$CI_COMMIT_SHA

deploy:
  stage: deploy
  script:
    - echo "Deploying to production"
  only:
    - main
  when: manual
```

## Jenkins Pipeline

```groovy
// Jenkinsfile
pipeline {
    agent any
    
    environment {
        DOCKER_IMAGE = 'myapp'
    }
    
    stages {
        stage('Build') {
            steps {
                sh 'docker build -t $DOCKER_IMAGE:$BUILD_NUMBER .'
            }
        }
        
        stage('Test') {
            steps {
                sh 'docker run $DOCKER_IMAGE:$BUILD_NUMBER pytest'
            }
        }
        
        stage('Deploy') {
            when {
                branch 'main'
            }
            steps {
                sh 'docker push $DOCKER_IMAGE:$BUILD_NUMBER'
                sh 'kubectl apply -f k8s/'
            }
        }
    }
    
    post {
        always {
            cleanWs()
        }
    }
}
```

## Local Testing with Act

```bash
# Install act
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Run GitHub Actions locally
act -l  # list workflows
act      # run workflow
```

## Docker Buildx

```bash
# Enable builder
docker buildx create --name mybuilder
docker buildx use mybuilder

# Build for ARM64
docker buildx build --platform linux/arm64 -t myapp:arm64 .

# Multi-platform build
docker buildx build --platform linux/amd64,linux/arm64 -t myapp:latest --push
```

## Test Containers

```yaml
services:
  postgres:
    image: postgres:15
    env:
      POSTGRES_PASSWORD: secret
    options: >-
      --health-cmd pg_isready
      --health-interval 10s
      --health-timeout 5s
      --health-retries 5
```

## Quality Gates

```bash
# Run tests with coverage
pytest --cov=. --cov-report=xml

# Check code quality
sonar-scanner

# Security scan
docker scan myapp:latest
```

## Deployment Strategies

```bash
# Blue-green deployment
kubectl apply -f deployment-blue.yaml
kubectl apply -f deployment-green.yaml

# Canary deployment
kubectl apply -f canary.yaml

# Rolling update
kubectl rollout status deployment/myapp
```

## Environment Configuration

```yaml
# .github/workflows/deploy.yml
jobs:
  deploy:
    environment:
      name: production
      url: https://myapp.com
    steps:
      - run: |
          echo "Deploying to production"
```

## Caching

```yaml
- name: Cache pip packages
  uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
    restore-keys: |
      ${{ runner.os }}-pip-

- name: Cache Docker layers
  uses: actions/cache@v4
  with:
    path: /tmp/.docker-builder-cache
    key: ${{ runner.os }}-docker-${{ github.sha }}
```

## Notifications

```yaml
- name: Discord Notification
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    fields: repo,message,commit,author
  env:
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```
