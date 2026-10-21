pipeline {
    agent any

    environment {
        DOCKER_IMAGE = "web-app:${BUILD_NUMBER}"
        QA_URL = "http://k3s-server:30081"
        REPORT_EMAIL = "josuebm912@gmail.com"
    }

    triggers {
        githubPush()
    }

    stages {
        stage('1. Checkout') {
            steps {
                checkout scm
            }
        }

        stage('2. Pruebas unitarias') {
            steps {
                echo 'Ejecutando pruebas unitarias con pytest...'
                sh 'python3 -m pytest -q tests/unit/'
            }
        }

        stage('3. Build de imagen temporal') {
            steps {
                echo 'Construyendo imagen Docker para análisis...'
                sh 'docker build -t "$DOCKER_IMAGE" .'
            }
        }

        stage('4. Escaneo de imagen (Trivy)') {
            steps {
                echo 'Buscando vulnerabilidades críticas con Trivy...'
                sh 'trivy image --severity CRITICAL --exit-code 1 --no-progress "$DOCKER_IMAGE"'
            }
        }

        stage('5. Despliegue QA (Kubernetes)') {
            when {
                branch 'ambiente-qa'
            }
            steps {
                sh "ansible-playbook -i ansible/inventory.ini ansible/deploy.yml -e env=qa"
                sh 'kubectl rollout status deployment/web-qa -n qa --timeout=180s'
            }
        }

        stage('6. Pruebas DAST (OWASP ZAP)') {
            when {
                branch 'ambiente-qa'
            }
            steps {
                sh '''docker run --rm --network net-qa \
                    -v "$(pwd):/zap/wrk/:rw" \
                    ghcr.io/zaproxy/zaproxy:stable zap-baseline.py \
                    -t "$QA_URL" -r zap_report.html'''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'zap_report.html', allowEmptyArchive: true
                }
            }
        }

        stage('7. Pruebas de carga (k6)') {
            when {
                branch 'ambiente-qa'
            }
            steps {
                sh '''docker run --rm --network net-qa \
                    -e QA_URL="$QA_URL" \
                    -v "$(pwd):/work" -w /work \
                    grafana/k6 run tests/load/k6-test.js'''
            }
        }

        stage('8. Aprobación y despliegue PRD') {
            when {
                branch 'main'
            }
            steps {
                script {
                    timeout(time: 1, unit: 'HOURS') {
                        input message: '¿Aprobar despliegue a Producción (PRD)?',
                              ok: 'Aprobar y desplegar',
                              submitter: 'admin,lead-devops'
                    }

                    try {
                        sh "ansible-playbook -i ansible/inventory.ini ansible/deploy.yml -e env=prd"
                        sh 'kubectl rollout status deployment/web-prd -n prd --timeout=180s'
                    } catch (err) {
                        echo 'Falló el despliegue PRD; intentando restaurar la revisión anterior.'
                        sh 'kubectl rollout undo deployment/web-prd -n prd || true'
                        throw err
                    }
                }
            }
        }
    }

    post {
        always {
            script {
                def reportStatus = currentBuild.currentResult ?: 'UNKNOWN'
                def commit = sh(
                    script: 'git rev-parse --short HEAD 2>/dev/null || echo unknown',
                    returnStdout: true
                ).trim()

                try {
                    sh """python3 /opt/devops/send_report.py \\
                        --recipient '$REPORT_EMAIL' \\
                        --status '${reportStatus}' \\
                        --job '$JOB_NAME' \\
                        --build-number '$BUILD_NUMBER' \\
                        --branch '${env.BRANCH_NAME ?: 'unknown'}' \\
                        --build-url '$BUILD_URL' \\
                        --commit '$commit'"""
                } catch (err) {
                    echo "No se pudo enviar el reporte por correo: ${err.getMessage()}"
                }
            }
            sh 'docker rmi "$DOCKER_IMAGE" --force || true'
        }
        aborted {
            echo 'Despliegue cancelado; no se aplicaron cambios adicionales a PRD.'
        }
        failure {
            echo 'El pipeline falló durante las pruebas, el análisis o el despliegue.'
        }
        success {
            echo 'Pipeline ejecutado con éxito.'
        }
    }
}