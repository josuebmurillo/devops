pipeline {
    agent any

    environment {
        DOCKER_IMAGE = "docker.io/library/web-app:pending"
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

        stage('2. Detectar cambios de la aplicación web') {
            steps {
                script {
                    def changedPaths = []
                    currentBuild.changeSets.each { changeSet ->
                        changeSet.items.each { entry ->
                            entry.affectedFiles.each { file -> changedPaths << file.path }
                        }
                    }

                    def relevantPrefixes = ['web/', 'tests/']
                    def relevantFiles = [
                        'Jenkinsfile',
                        'ansible/deploy.yml',
                        'k8s/deploy-qa.yml',
                        'k8s/deploy-prd.yaml'
                    ]
                    def firstBuild = currentBuild.previousBuild == null
                    def appChanged = firstBuild || changedPaths.any { path ->
                        relevantFiles.contains(path) || relevantPrefixes.any { prefix -> path.startsWith(prefix) }
                    }

                    env.WEB_APP_CHANGED = appChanged.toString()
                    if (appChanged) {
                        echo "Se detectaron cambios relevantes: ${changedPaths.join(', ')}"
                    } else {
                        echo 'Sin cambios en la aplicación, pruebas o despliegue web; se omiten sus etapas.'
                    }
                }
            }
        }

        stage('3. Pruebas unitarias') {
            when {
                expression { env.WEB_APP_CHANGED == 'true' }
            }
            steps {
                echo 'Ejecutando pruebas unitarias con pytest...'
                sh 'python3 -m pytest -q tests/unit/'
            }
        }

        stage('4. Build de imagen temporal') {
            when {
                expression { env.WEB_APP_CHANGED == 'true' }
            }
            steps {
                echo 'Construyendo imagen de la aplicación web estática...'
                script {
                    def commitTag = sh(
                        script: 'git rev-parse --short=12 HEAD',
                        returnStdout: true
                    ).trim()
                    env.DOCKER_IMAGE = "docker.io/library/web-app:${commitTag}"
                }
                sh 'docker build -f web/Dockerfile -t "$DOCKER_IMAGE" .'
            }
        }

        stage('5. Prueba HTTP de la aplicación') {
            when {
                expression { env.WEB_APP_CHANGED == 'true' }
            }
            steps {
                sh '''set -eu
                    SMOKE_CONTAINER="web-app-smoke-${BUILD_NUMBER}"
                    cleanup() { docker rm --force "$SMOKE_CONTAINER" >/dev/null 2>&1 || true; }
                    trap cleanup EXIT
                    docker run --detach --name "$SMOKE_CONTAINER" --network net-qa "$DOCKER_IMAGE"
                    curl --retry 10 --retry-connrefused --retry-delay 1 --fail --silent \
                        "http://${SMOKE_CONTAINER}/health" -o /tmp/web-health.txt
                    grep -q '^ok' /tmp/web-health.txt
                    curl --retry 5 --retry-connrefused --retry-delay 1 --fail --silent \
                        "http://${SMOKE_CONTAINER}/" -o /tmp/web-index.html
                    grep -q 'DevOps Lab' /tmp/web-index.html
                    grep -q 'Aplicación operativa' /tmp/web-index.html
                    echo 'Smoke test HTTP aprobado.'
                '''
            }
        }

        stage('6. Escaneo de imagen (Trivy)') {
            when {
                expression { env.WEB_APP_CHANGED == 'true' }
            }
            steps {
                echo 'Buscando vulnerabilidades críticas con Trivy...'
                sh 'trivy image --severity CRITICAL --exit-code 1 --no-progress "$DOCKER_IMAGE"'
            }
        }

        stage('7. Cargar imagen aprobada en K3s') {
            when {
                expression { env.WEB_APP_CHANGED == 'true' }
            }
            steps {
                sh '''set -eu
                    IMAGE_ARCHIVE="$WORKSPACE/web-app-${BUILD_NUMBER}.tar"
                    docker save "$DOCKER_IMAGE" --output "$IMAGE_ARCHIVE"
                    docker exec -i k3s-server ctr --namespace k8s.io images import - < "$IMAGE_ARCHIVE"
                    rm -f "$IMAGE_ARCHIVE"
                    docker exec k3s-server ctr --namespace k8s.io images ls --quiet | grep -Fx "$DOCKER_IMAGE"
                '''
            }
        }

        stage('8. Despliegue QA (Kubernetes)') {
            when {
                allOf {
                    branch 'ambiente-qa'
                    expression { env.WEB_APP_CHANGED == 'true' }
                }
            }
            steps {
                sh "/usr/local/bin/kubeconfig-entrypoint.sh ansible-playbook -i ansible/inventory.ini ansible/deploy.yml -e 'env=qa web_image=${DOCKER_IMAGE}'"
                sh '/usr/local/bin/kubeconfig-entrypoint.sh kubectl rollout status deployment/web-qa -n qa --timeout=180s'
            }
        }

        stage('9. Pruebas DAST (OWASP ZAP)') {
            when {
                allOf {
                    branch 'ambiente-qa'
                    expression { env.WEB_APP_CHANGED == 'true' }
                }
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

        stage('10. Pruebas de carga (k6)') {
            when {
                allOf {
                    branch 'ambiente-qa'
                    expression { env.WEB_APP_CHANGED == 'true' }
                }
            }
            steps {
                sh '''docker run --rm --network net-qa \
                    -e QA_URL="$QA_URL" \
                    -v "$(pwd):/work" -w /work \
                    grafana/k6 run tests/load/k6-test.js'''
            }
        }

        stage('11. Aprobación y despliegue PRD') {
            when {
                allOf {
                    branch 'main'
                    expression { env.WEB_APP_CHANGED == 'true' }
                }
            }
            steps {
                script {
                    timeout(time: 1, unit: 'HOURS') {
                        input message: '¿Aprobar despliegue a Producción (PRD)?',
                              ok: 'Aprobar y desplegar',
                              submitter: 'admin,lead-devops'
                    }

                    try {
                        sh "/usr/local/bin/kubeconfig-entrypoint.sh ansible-playbook -i ansible/inventory.ini ansible/deploy.yml -e 'env=prd web_image=${DOCKER_IMAGE}'"
                        sh '/usr/local/bin/kubeconfig-entrypoint.sh kubectl rollout status deployment/web-prd -n prd --timeout=180s'
                    } catch (err) {
                        echo 'Falló el despliegue PRD; intentando restaurar la revisión anterior.'
                        sh '/usr/local/bin/kubeconfig-entrypoint.sh kubectl rollout undo deployment/web-prd -n prd || true'
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
            script {
                if (env.WEB_APP_CHANGED == 'true') {
                    sh 'docker rmi "$DOCKER_IMAGE" --force || true'
                }
            }
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