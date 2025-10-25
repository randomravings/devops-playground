FROM jenkins/jenkins:lts

USER root

# Install maven (allows building maven projects directly on the master - ok for playground)
RUN apt-get update \
 && apt-get install -y maven ca-certificates curl unzip \
 && rm -rf /var/lib/apt/lists/*

# Copy plugins list and CLI wrapper
COPY plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli -f /usr/share/jenkins/ref/plugins.txt || true

# Copy Jenkins CLI wrapper
COPY jenkins-cli.sh /usr/local/bin/jenkins-cli
RUN chmod +x /usr/local/bin/jenkins-cli

USER jenkins
