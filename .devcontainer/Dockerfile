FROM mcr.microsoft.com/devcontainers/base:ubuntu-22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# --- OS packages -----------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ca-certificates \
    gnupg \
    lsb-release \
    software-properties-common \
    unzip \
    zip \
    git \
    postgresql-client \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# --- Python 3.11 -----------------------------------------------------------
RUN add-apt-repository -y ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
       python3.11 python3.11-venv python3.11-dev \
    && update-alternatives --install /usr/local/bin/python python /usr/bin/python3.11 100 \
    && update-alternatives --install /usr/local/bin/python3 python3 /usr/bin/python3.11 100 \
    && rm -rf /var/lib/apt/lists/*

# --- uv (fast Python package manager) -------------------------------------
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && mv /root/.local/bin/uv /usr/local/bin/uv \
    && mv /root/.local/bin/uvx /usr/local/bin/uvx

# --- Node.js 20 ------------------------------------------------------------
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# --- Terraform -------------------------------------------------------------
# dpkg arch (amd64/arm64) matches HashiCorp's release naming, so this works on
# both Intel and Apple Silicon hosts.
ARG TERRAFORM_VERSION=1.9.8
RUN TF_ARCH="$(dpkg --print-architecture)" \
    && curl -sLo /tmp/tf.zip "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_${TF_ARCH}.zip" \
    && unzip -o /tmp/tf.zip -d /usr/local/bin/ \
    && rm /tmp/tf.zip \
    && chmod +x /usr/local/bin/terraform

# --- gcloud CLI + Cloud SQL Auth Proxy -------------------------------------
# The apt package `google-cloud-cli-cloud-sql-proxy` is only published for
# amd64, so on arm64 (Apple Silicon) `apt-get install` fails with
# "Unable to locate package". Install the gcloud CLI from apt, then fetch the
# Cloud SQL Auth Proxy as a standalone arch-matched binary (it ships arm64).
ARG CLOUD_SQL_PROXY_VERSION=2.11.0
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" \
      > /etc/apt/sources.list.d/google-cloud-sdk.list \
    && curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg \
       | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg \
    && apt-get update \
    && apt-get install -y google-cloud-cli \
    && rm -rf /var/lib/apt/lists/* \
    && PROXY_ARCH="$(dpkg --print-architecture)" \
    && curl -fsSLo /usr/local/bin/cloud-sql-proxy \
       "https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v${CLOUD_SQL_PROXY_VERSION}/cloud-sql-proxy.linux.${PROXY_ARCH}" \
    && chmod +x /usr/local/bin/cloud-sql-proxy

# --- Docker CLI (for using the host's docker socket) ----------------------
RUN install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && chmod a+r /etc/apt/keyrings/docker.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
       > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y docker-ce-cli docker-compose-plugin \
    && rm -rf /var/lib/apt/lists/*

# --- Global npm tools ------------------------------------------------------
RUN npm install -g pnpm@latest

# --- Non-root user setup (base image already has "vscode" uid 1000) --------
# Allow vscode user to use the docker socket via group
RUN groupadd -f docker && usermod -aG docker vscode

USER vscode
WORKDIR /workspace
