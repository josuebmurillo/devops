FROM jenkins/jenkins:lts

USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    docker.io \
    gnupg \
    lsb-release \
    python3 \
    python3-pip \
    wget && \
    wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | gpg --dearmor -o /usr/share/keyrings/trivy.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/trivy.gpg] https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" > /etc/apt/sources.list.d/trivy.list && \
    apt-get update && apt-get install -y --no-install-recommends trivy && \
    KUBECTL_VERSION="$(curl -fsSL https://dl.k8s.io/release/stable.txt)" && \
    curl -fsSLo /usr/local/bin/kubectl "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl" && \
    chmod +x /usr/local/bin/kubectl && \
    python3 -m pip install --break-system-packages --no-cache-dir \
      ansible==10.6.0 kubernetes==31.0.0 pytest==8.3.3 && \
    rm -rf /var/lib/apt/lists/*

COPY ansible/requirements.yml /tmp/ansible-requirements.yml
RUN ansible-galaxy collection install -p /usr/share/ansible/collections -r /tmp/ansible-requirements.yml

COPY scripts/kubeconfig-entrypoint.sh /usr/local/bin/kubeconfig-entrypoint.sh
RUN chmod +x /usr/local/bin/kubeconfig-entrypoint.sh

COPY app/notifications.py /opt/devops/notifications.py
COPY scripts/send_report.py /opt/devops/send_report.py

ENV ANSIBLE_COLLECTIONS_PATH=/usr/share/ansible/collections
ENV PATH="/usr/local/bin:${PATH}"

ENTRYPOINT ["/usr/local/bin/kubeconfig-entrypoint.sh"]
CMD ["/usr/bin/tini", "--", "/usr/local/bin/jenkins.sh"]