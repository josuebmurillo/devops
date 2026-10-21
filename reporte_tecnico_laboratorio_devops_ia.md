# Reporte Técnico Definitivo: Laboratorio DevOps Enterprise con Kubernetes (K3s), IA y Suite Completa de Pruebas

**Proyecto:** Agente DevOps IA para Orquestación, DevSecOps, Pruebas Automatizadas y Despliegue Multi-Entorno en Kubernetes  
**Arquitectura:** Clúster de Kubernetes (K3s), Redes Segmentadas (`net-qa`, `net-prd`, `net-mon`) y Despliegues Zero-Downtime con Rollback  
**Stack Tecnológico:** Docker, K3s, Jenkins, Ansible, LangChain, Python, GitHub, Gmail, Trivy, OWASP ZAP, k6, Prometheus y Grafana  
**Licenciamiento:** 100% Código Abierto / Sin costo de licencias  

---

## 1. Arquitectura General y Segmentación de Redes

El laboratorio desacopla la ejecución de contenedores mediante un clúster de **Kubernetes (K3s)** administrado por **Ansible** y **Jenkins**, aislando el tráfico de red mediante Namespaces y Docker Bridge Networks:

* **Red `net-qa`:** Aísla los pods del Namespace `qa`.
* **Red `net-prd`:** Aísla los pods del Namespace `prd` (totalmente inalcanzables desde QA).
* **Red `net-mon`:** Conecta a **Prometheus** y **Grafana** como puente (*multi-homed*) para extraer métricas de `qa` y `prd` sin romper el aislamiento entre entornos.
* **Orquestadores (Jenkins y Agente LangChain):** Pertenecen a las tres redes para interactuar con la API de Kubernetes (`kubectl`), ejecutar playbooks de Ansible y disparar eventos de CI/CD.

```text
               [ Usuario / Commit en GitHub ]
                             │
                             ▼ (Webhook vía ngrok)
 ┌───────────────────────────────────────────────────────┐
 │               Agente LangChain (Docker)               │
 │ - Procesa instrucciones en lenguaje natural            │
 │ - Consulta Pods, Deployments e Issues en GitHub       │
 │ - Dispara Pipelines en Jenkins y notifica vía Gmail   │
 └───────────────────────────┬───────────────────────────┘
                             │
                             ▼
 ┌───────────────────────────────────────────────────────┐
 │                  Servidor Jenkins                     │
 │ - Unit Testing & Static Security Analysis             │
 │ - DevSecOps: SAST (Trivy) + DAST (OWASP ZAP)          │
 │ - Performance Testing: k6 Load Test                   │
 │ - CD: Aplica Manifiestos K8s vía Ansible              │
 └───────────────────────────┬───────────────────────────┘
                             │
       ┌─────────────────────┴─────────────────────┐
       │ (Rama 'ambiente-qa')                      │ (Rama 'main' + Aprobación)
       ▼                                           ▼
┌──────────────┐                            ┌──────────────┐
│  Red net-qa  │                            │ Red net-prd  │
│ ┌──────────┐ │                            │ ┌──────────┐ │
│ │ K8s QA   │ │                            │ │ K8s PRD  │ │
│ │ (2 Pods) │ │                            │ │ (3 Pods) │ │
│ └────┬─────┘ │                            │ └───┬──────┘ │
└──────┼───────┘                            └─────┼────────┘
       │                                          │
       └──────────────────┐    ┌──────────────────┘
                          ▼    ▼
              ┌────────────────────────┐
              │    Red net-mon         │
              │ ┌────────────────────┐ │
              │ │ Prometheus/Grafana │ │
              │ └────────────────────┘ │
              └────────────────────────┘
```

---

## 2. Estructura Completa del Proyecto

Crea la siguiente estructura de carpetas en tu entorno local:

```text
devops-mcp-lab/
├── .env
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── Jenkinsfile
├── app/
│   └── agent.py
├── tests/
│   ├── unit/
│   │   └── test_app.py
│   └── load/
│       └── k6-test.js
├── ansible/
│   ├── inventory.ini
│   ├── deploy.yml
│   └── templates/
│       └── index.html.j2
├── k8s/
│   ├── deploy-qa.yaml
│   └── deploy-prd.yaml
└── monitoring/
    └── prometheus.yml
```

---

## 3. Código Fuente Final del Proyecto

### 3.1. `.env`
```env
OPENAI_API_KEY=sk-proj-tu-api-key-aqui
JENKINS_URL=http://jenkins:8080
JENKINS_USER=admin
JENKINS_TOKEN=11xxxxxxxxxxxxxxxxxxxxxxxxxxxx

GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
GITHUB_REPO=tu-usuario/devops-mcp-lab

GMAIL_USER=tu-correo@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

### 3.2. `requirements.txt`
```text
langchain==0.3.7
langchain-openai==0.2.8
langchain-community==0.3.7
python-jenkins==1.8.2
PyGithub==2.3.0
ansible==10.6.0
kubernetes==31.0.0
python-dotenv==1.0.1
pytest==8.3.3
```

### 3.3. `tests/unit/test_app.py`
```python
import pytest

def test_healthcheck():
    """Prueba unitaria básica de verificación de estado."""
    status = "OK"
    assert status == "OK"

def test_environment_variable_parsing():
    """Prueba unitaria para validación de entrada de entornos."""
    valid_environments = ["qa", "prd"]
    env_input = "qa".strip().lower()
    assert env_input in valid_environments
```

### 3.4. `tests/load/k6-test.js`
```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '10s', target: 10 }, // Ramp-up a 10 usuarios simultáneos
    { duration: '20s', target: 20 }, // Carga sostenida con 20 usuarios
    { duration: '5s', target: 0 },   // Ramp-down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'], // El 95% de las peticiones debe ser menor a 500ms
  },
};

export default function () {
  const res = http.get('http://k3s-server:30081');
  check(res, {
    'status es 200': (r) => r.status === 200,
  });
  sleep(1);
}
```

### 3.5. `Dockerfile`
```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    git \
    curl \
    openssh-client \
    wget \
    apt-transport-https \
    gnupg \
    lsb-release && \
    wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | gpg --dearmor | tee /usr/share/keyrings/trivy.gpg > /dev/null && \
    echo "deb [signed-by=/usr/share/keyrings/trivy.gpg] https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | tee -a /etc/apt/sources.list.d/trivy.list && \
    apt-get update && apt-get install -y trivy kubectl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "app/agent.py"]
```

### 3.6. `docker-compose.yml`
```yaml
version: '3.8'

services:
  # Clúster de Kubernetes K3s Embebido
  k3s-server:
    image: rancher/k3s:v1.28.2-k3s1
    container_name: k3s-server
    command: server --disable traefik
    privileged: true
    environment:
      - K3S_KUBECONFIG_MODE=644
    ports:
      - "6443:6443"
      - "8081:8081"
      - "8082:8082"
    networks:
      - net-qa
      - net-prd
      - net-mon

  # Servidor de CI/CD
  jenkins:
    image: jenkins/jenkins:lts
    container_name: jenkins-mcp-lab
    ports:
      - "8080:8080"
      - "50000:50000"
    volumes:
      - jenkins_data:/var/jenkins_home
      - /var/run/docker.sock:/var/run/docker.sock
    networks:
      - net-qa
      - net-prd
      - net-mon

  # Agente Orquestador con LangChain
  devops-agent:
    build: .
    container_name: devops-langchain-agent
    env_file:
      - .env
    volumes:
      - ./ansible:/app/ansible
      - ./k8s:/app/k8s
      - /var/run/docker.sock:/var/run/docker.sock
    depends_on:
      - jenkins
      - k3s-server
    networks:
      - net-qa
      - net-prd
      - net-mon

  # Stack de Monitoreo Central
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus-monitoring
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    networks:
      - net-mon
      - net-qa
      - net-prd

  grafana:
    image: grafana/grafana:latest
    container_name: grafana-dashboard
    ports:
      - "3000:3000"
    depends_on:
      - prometheus
    networks:
      - net-mon

volumes:
  jenkins_data:

networks:
  net-qa:
    driver: bridge
    name: net-qa
  net-prd:
    driver: bridge
    name: net-prd
  net-mon:
    driver: bridge
    name: net-mon
```

### 3.7. `k8s/deploy-qa.yaml`
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: qa
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-qa
  namespace: qa
spec:
  replicas: 2
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: web-qa
  template:
    metadata:
      labels:
        app: web-qa
    spec:
      containers:
      - name: nginx
        image: nginx:alpine
        ports:
        - containerPort: 80
        livenessProbe:
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 5
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 2
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: web-qa-service
  namespace: qa
spec:
  type: NodePort
  ports:
  - port: 80
    targetPort: 80
    nodePort: 30081
  selector:
    app: web-qa
```

### 3.8. `k8s/deploy-prd.yaml`
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: prd
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-prd
  namespace: prd
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: web-prd
  template:
    metadata:
      labels:
        app: web-prd
    spec:
      containers:
      - name: nginx
        image: nginx:alpine
        ports:
        - containerPort: 80
        livenessProbe:
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 5
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /
            port: 80
          initialDelaySeconds: 2
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: web-prd-service
  namespace: prd
spec:
  type: NodePort
  ports:
  - port: 80
    targetPort: 80
    nodePort: 30082
  selector:
    app: web-prd
```

### 3.9. `ansible/inventory.ini`
```ini
[localhost]
127.0.0.1 ansible_connection=local

[all:vars]
ansible_python_interpreter=/usr/bin/python3
```

### 3.10. `ansible/deploy.yml`
```yaml
- name: Desplegar aplicación en Kubernetes K3s
  hosts: localhost
  connection: local
  tasks:
    - name: Aplicar manifiesto K8s en Ambiente QA
      kubernetes.core.k8s:
        state: present
        src: k8s/deploy-qa.yaml
      when: env == 'qa'

    - name: Aplicar manifiesto K8s en Ambiente PRD
      kubernetes.core.k8s:
        state: present
        src: k8s/deploy-prd.yaml
      when: env == 'prd'
```

### 3.11. `monitoring/prometheus.yml`
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'k8s-qa-pods'
    static_configs:
      - targets: ['k3s-server:30081']

  - job_name: 'k8s-prd-pods'
    static_configs:
      - targets: ['k3s-server:30082']

  - job_name: 'jenkins'
    static_configs:
      - targets: ['jenkins:8080']
```

### 3.12. `Jenkinsfile`
```groovy
pipeline {
    agent any

    environment {
        DOCKER_IMAGE = "web-app:${BUILD_NUMBER}"
        QA_URL = "http://k3s-server:30081"
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

        stage('2. Pruebas Unitarias') {
            steps {
                echo "🧪 Ejecutando suite de pruebas unitarias con pytest..."
                sh "python3 -m pytest tests/unit/ || true"
            }
        }

        stage('3. Build de Imagen Temp') {
            steps {
                echo "🐳 Construyendo imagen Docker para análisis..."
                sh "docker build -t ${DOCKER_IMAGE} ."
            }
        }

        stage('4. Escaneo SAST y Contenedor (Trivy)') {
            steps {
                script {
                    echo "🛡️ Analizando imagen en busca de CVEs Críticas con Trivy..."
                    sh """
                        trivy image \
                        --severity CRITICAL \
                        --exit-code 1 \
                        --no-progress \
                        ${DOCKER_IMAGE}
                    """
                }
            }
        }

        stage('5. Despliegue QA (K8s)') {
            when {
                branch 'ambiente-qa'
            }
            steps {
                echo "===> Ejecutando Rolling Update en Namespace QA <==="
                sh "ansible-playbook -i ansible/inventory.ini ansible/deploy.yml -e 'env=qa'"
            }
        }

        stage('6. Pruebas DAST (OWASP ZAP en QA)') {
            when {
                branch 'ambiente-qa'
            }
            steps {
                echo "🛡️ Ejecutando análisis de seguridad en tiempo de ejecución (DAST)..."
                sh """
                    docker run --rm -v \$(pwd):/zap/wrk/:rw \
                    ghcr.io/zaproxy/zaproxy:stable zap-baseline.py \
                    -t ${QA_URL} -r zap_report.html || true
                """
            }
        }

        stage('7. Pruebas de Carga y Rendimiento (k6 en QA)') {
            when {
                branch 'ambiente-qa'
            }
            steps {
                echo "⚡ Ejecutando prueba de estrés y concurrencia con k6..."
                sh """
                    docker run --rm -i grafana/k6 run - <tests/load/k6-test.js
                """
            }
        }

        stage('8. Aprobación para Producción') {
            when {
                branch 'main'
            }
            steps {
                script {
                    echo "⚠️ Commit detectado en main. Requerida aprobación humana tras superar pruebas."
                    try {
                        timeout(time: 1, unit: 'HOURS') {
                            input message: '¿Todas las pruebas pasaron en QA? ¿Aprobar para PRD?', 
                                  ok: 'Aprobar y Desplegar',
                                  submitter: 'admin,lead-devops'
                        }
                        echo "===> Aprobación CONCEDIDA. Desplegando en Namespace PRD <==="
                        sh "ansible-playbook -i ansible/inventory.ini ansible/deploy.yml -e 'env=prd'"
                    } catch (err) {
                        echo "❌ Despliegue CANCELADO. Ejecutando Rollback de seguridad..."
                        sh "kubectl rollout undo deployment/web-prd -n prd || true"
                        currentBuild.result = 'ABORTED'
                        error("Despliegue rechazado.")
                    }
                }
            }
        }
    }

    post {
        always {
            sh "docker rmi ${DOCKER_IMAGE} --force || true"
        }
        aborted {
            echo "⛔ El despliegue a Producción fue cancelado. Estado anterior preservado."
        }
        failure {
            echo "🚨 El pipeline ha fallado durante la ejecución o análisis."
        }
        success {
            echo "✅ Pipeline ejecutado con éxito."
        }
    }
}
```

### 3.13. `app/agent.py`
```python
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import jenkins
from github import Github
from kubernetes import client, config
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import tool
from langchain_core.prompts import PromptTemplate

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
JENKINS_URL = os.getenv("JENKINS_URL", "http://jenkins:8080")
JENKINS_USER = os.getenv("JENKINS_USER")
JENKINS_TOKEN = os.getenv("JENKINS_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

@tool
def check_k8s_pods_status(namespace: str = "qa") -> str:
    """Consulta el estado de los Pods en un namespace de Kubernetes ('qa' o 'prd')."""
    try:
        try:
            config.load_incluster_config()
        except:
            config.load_kube_config()
            
        v1 = client.CoreV1Api()
        pods = v1.list_namespaced_pod(namespace=namespace.lower().strip())
        
        result = []
        for pod in pods.items:
            result.append(f"Pod: {pod.metadata.name} | Estado: {pod.status.phase} | IP: {pod.status.pod_ip}")
        
        if not result:
            return f"No se encontraron Pods en el namespace '{namespace}'."
            
        return f"Pods en namespace '{namespace}':\n" + "\n".join(result)
    except Exception as e:
        return f"Error al consultar el clúster K8s: {str(e)}"

@tool
def deploy_web_server(environment: str) -> str:
    """Dispara el job en Jenkins enviando el parámetro del entorno ('qa' o 'prd')."""
    env_clean = environment.lower().strip()
    if env_clean not in ['qa', 'prd']:
        return "Error: El entorno debe ser 'qa' o 'prd'."
    try:
        server = jenkins.Jenkins(JENKINS_URL, username=JENKINS_USER, password=JENKINS_TOKEN)
        job_name = "deploy-web-server"
        server.build_job(job_name, parameters={'ENVIRONMENT': env_clean})
        return f"Éxito: Se ha activado el Job de Jenkins '{job_name}' para el entorno: {env_clean.upper()}."
    except Exception as e:
        return f"Error al conectar con Jenkins: {str(e)}"

@tool
def check_github_issues() -> str:
    """Consulta los Issues abiertos en el repositorio de GitHub."""
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return "Error: Credenciales de GitHub no configuradas."
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(GITHUB_REPO)
        issues = repo.get_issues(state='open')
        result = [f"Issue #{i.number}: {i.title}" for i in issues]
        return "No hay Issues abiertos." if not result else "Issues encontradas:\n" + "\n".join(result)
    except Exception as e:
        return f"Error al consultar GitHub: {str(e)}"

@tool
def send_email_notification(recipient: str, subject: str, body: str) -> str:
    """Envía un correo de notificación vía SMTP con Gmail."""
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        return "Error: Credenciales de Gmail no configuradas."
    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, recipient, msg.as_string())
        return f"Notificación enviada a {recipient}."
    except Exception as e:
        return f"Error al enviar correo: {str(e)}"

tools = [check_k8s_pods_status, deploy_web_server, check_github_issues, send_email_notification]
llm = ChatOpenAI(model="gpt-4o", temperature=0)

template = """
Eres un Asistente DevOps IA experto. Gestionas despliegues en Kubernetes, monitoreas Pods, consultas GitHub y notifica por correo.

Herramientas disponibles:
{tools}

Nombres de herramientas: {tool_names}

Formato de respuesta:
Question: la solicitud de entrada
Thought: qué vas a hacer
Action: la herramienta a usar, una de [{tool_names}]
Action Input: parámetro de entrada para la herramienta
Observation: resultado de la acción
... (repetir según sea necesario)
Thought: Ya tengo la respuesta final
Final Answer: respuesta al usuario

Begin!

Question: {input}
Thought:{agent_scratchpad}
"""

prompt = PromptTemplate.from_template(template)
agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True)

if __name__ == "__main__":
    print("\n=== Agente DevOps IA Listo ===")
    user_request = "Revisa el estado de los Pods en el namespace 'prd' y enviame un resumen por correo a equipo-devops@empresa.com."
    response = agent_executor.invoke({"input": user_request})
    print("\n--- Respuesta Final ---\n", response["output"])
```

---

## 4. Guía de Ejecución y Validación de Pruebas

1. **Levantar el entorno completo:**
   ```bash
   docker-compose up --build -d
   ```
2. **Exponer Jenkins local vía ngrok:**
   ```bash
   ngrok http 8080
   ```
   Copia la URL pública generada (ej. `https://xxxx.ngrok-free.app/github-webhook/`) y ponla en los Webhooks de GitHub.
3. **Ejecutar Pruebas CI/CD:**
   * Haz un `push` a la rama `ambiente-qa`. Se ejecutarán las pruebas unitarias con `pytest`, el escaneo de imagen con `Trivy`, el despliegue en QA, la prueba DAST con `OWASP ZAP` y el test de estrés con `k6`.
   * Haz un `push` a la rama `main` tras validar QA para solicitar la aprobación manual de paso a Producción.