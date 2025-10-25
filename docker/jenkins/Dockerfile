FROM jenkins/jenkins:latest-jdk21

USER root

# Install maven (allows building maven projects directly on the master - ok for playground)
RUN apt-get update \
 && apt-get install -y maven ca-certificates curl unzip \
 && rm -rf /var/lib/apt/lists/*

# Copy plugins list and CLI wrapper
COPY plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli -f /usr/share/jenkins/ref/plugins.txt

# Copy Jenkins CLI wrapper
COPY jenkins-cli.sh /usr/local/bin/jenkins-cli
RUN chmod +x /usr/local/bin/jenkins-cli


ENV DEBIAN_FRONTEND=noninteractive

# OS deps (incl. python3-venv for creating venvs) + UTF-8 locale
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      python3 python3-venv python3-pip \
      pgformatter \
      diffutils \
      git openssh-client \
      curl jq ca-certificates \
      locales \
    && sed -i 's/# *en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen \
    && locale-gen && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ENV LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8

# Create a tools venv and install Python CLIs there
# (Avoids system-wide pip installs, solves PEP 668)
RUN python3 -m venv /opt/dbci-venv && \
    /opt/dbci-venv/bin/pip install --upgrade pip && \
    /opt/dbci-venv/bin/pip install "sqlfluff>=3.0.0"

# Expose the venv tools on PATH for all users
ENV PATH="/opt/dbci-venv/bin:${PATH}"

# Optional: also symlink specific binaries if you prefer
RUN ln -sf /opt/dbci-venv/bin/sqlfluff /usr/local/bin/sqlfluff

# --- OPTIONAL (commented) — enable later when you reintroduce DB checks ---
# RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client && rm -rf /var/lib/apt/lists/*
# RUN curl -fsSL https://github.com/k0kubun/sqldef/releases/latest/download/pgsqldef_linux_amd64.tar.gz \
#     | tar -xz -C /usr/local/bin pgsqldef && chmod +x /usr/local/bin/pgsqldef
# RUN python3 -m pip install --no-cache-dir "migra[pg]" sqlparse
# --------------------------------------------------------------------------

    
# Drop back to jenkins user for pipeline execution
USER jenkins

# Helpful defaults (optional)
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1