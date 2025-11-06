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

# Install build dependencies for Python 3.12
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential \
      zlib1g-dev \
      libncurses5-dev \
      libgdbm-dev \
      libnss3-dev \
      libssl-dev \
      libreadline-dev \
      libffi-dev \
      libsqlite3-dev \
      libbz2-dev \
      liblzma-dev \
      wget \
    && rm -rf /var/lib/apt/lists/*

# Download and install Python 3.12
RUN cd /tmp && \
    wget https://www.python.org/ftp/python/3.12.7/Python-3.12.7.tar.xz && \
    tar -xf Python-3.12.7.tar.xz && \
    cd Python-3.12.7 && \
    ./configure --enable-optimizations --prefix=/usr/local && \
    make -j$(nproc) && \
    make altinstall && \
    cd / && \
    rm -rf /tmp/Python-3.12.7*

# Create symlinks for python3.12
RUN ln -sf /usr/local/bin/python3.12 /usr/bin/python3.12 && \
    ln -sf /usr/local/bin/pip3.12 /usr/bin/pip3.12

# OS deps + UTF-8 locale
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      pgformatter \
      diffutils \
      git openssh-client \
      curl jq ca-certificates \
      locales \
    && sed -i 's/# *en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen \
    && locale-gen && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Docker CLI (for Atlas docker:// dev URLs)
RUN curl -fsSL https://get.docker.com | sh

# Fix Docker socket permissions for Jenkins user
# The docker group GID in the container needs to match the host's docker group
# We'll handle this at runtime with an entrypoint script
RUN usermod -aG docker jenkins

ENV LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8

# Create a tools venv and install Python CLIs there
# (Avoids system-wide pip installs, solves PEP 668)
RUN python3.12 -m venv /opt/dbci-venv && \
    /opt/dbci-venv/bin/pip install --upgrade pip && \
    /opt/dbci-venv/bin/pip install "sqlfluff>=3.0.0"

# Expose the venv tools on PATH for all users
ENV PATH="/opt/dbci-venv/bin:${PATH}"

# Optional: also symlink specific binaries if you prefer
RUN ln -sf /opt/dbci-venv/bin/sqlfluff /usr/local/bin/sqlfluff

# Install Atlas CLI for database schema management and diffing
RUN curl -sSf https://atlasgo.sh | sh

# Copy and set up custom entrypoint for Docker socket permissions
COPY entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# --- OPTIONAL (commented) — enable later when you reintroduce DB checks ---
# RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client && rm -rf /var/lib/apt/lists/*
# RUN curl -fsSL https://github.com/k0kubun/sqldef/releases/latest/download/pgsqldef_linux_amd64.tar.gz \
#     | tar -xz -C /usr/local/bin pgsqldef && chmod +x /usr/local/bin/pgsqldef
# RUN python3 -m pip install --no-cache-dir "migra[pg]" sqlparse
# --------------------------------------------------------------------------

    
# Drop back to jenkins user for pipeline execution
USER jenkins

# Set custom entrypoint to fix Docker socket permissions
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# Helpful defaults (optional)
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1