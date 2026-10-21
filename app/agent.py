import os
import jenkins
from github import Github
from kubernetes import client, config
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import tool
from langchain_core.prompts import PromptTemplate
from app.notifications import send_email

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
    namespace = namespace.strip().strip("'\"").lower()
    if namespace not in {"qa", "prd"}:
        return "Error: El namespace debe ser 'qa' o 'prd'."

    try:
        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config()
            
        v1 = client.CoreV1Api()
        pods = v1.list_namespaced_pod(namespace=namespace)
        
        result = []
        for pod in pods.items:
            result.append(
                f"Pod: {pod.metadata.name} | Estado: {pod.status.phase} | IP: {pod.status.pod_ip}"
            )
        
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
    return send_email(
        recipient=recipient,
        subject=subject,
        body=body,
        sender=GMAIL_USER,
        app_password=GMAIL_APP_PASSWORD,
    )

tools = [check_k8s_pods_status, deploy_web_server, check_github_issues, send_email_notification]
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

template = """
Eres un Asistente DevOps IA experto. Gestionas despliegues en Kubernetes, monitoreas Pods, consultas GitHub y notificas por correo.
Usa únicamente las herramientas necesarias para cumplir la solicitud explícita. No inventes acciones adicionales: nunca despliegues, consultes otros servicios ni envíes correos si el usuario no lo pidió expresamente. Si una herramienta devuelve un error, informa del error; no pruebes acciones ajenas como alternativa.

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
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    handle_parsing_errors=True,
    max_iterations=5,
)

if __name__ == "__main__":
    print("\n=== Agente DevOps IA Listo ===")
    user_request = "Revisa el estado de los Pods en el namespace 'qa'."
    startup_tools = [check_k8s_pods_status]
    startup_agent = create_react_agent(llm=llm, tools=startup_tools, prompt=prompt)
    startup_executor = AgentExecutor(
        agent=startup_agent,
        tools=startup_tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=3,
    )
    response = startup_executor.invoke({"input": user_request})
    print("\n--- Respuesta Final ---\n", response["output"])