# Self-hosted GitHub Actions runner for this repo (docs/VPS_RUNNER.md). Built and started by vps-setup.sh, which carries
# an identical copy of this file (heredoc) — change both together (tests/test_vps_runner.py checks they match).
# Base: official runner image 2.338.1 (ghcr.io, created 22.10.2026, Ubuntu 24.04), pinned by its index digest.
# The runner updates itself to newer releases at run time (GitHub requires current runners); the pin fixes the build.
FROM ghcr.io/actions/actions-runner:2.338.1@sha256:e275409999c37162649aa050ca573f03eab2eabcb3a1e7fcc47548de6b4f9690

USER root
# What the workflows install at run time (process-proposal.yml "Install tools" apt line, copied exactly:
# poppler-utils tesseract-ocr tesseract-ocr-mar libreoffice-writer fonts-freefont-ttf) plus the sandbox / hook tools.
# python3 brings the shared libraries (libffi, sqlite, readline) that setup-python's prebuilt Python 3.12 needs.
RUN apt-get update -y \
 && apt-get install -y --no-install-recommends \
      poppler-utils tesseract-ocr tesseract-ocr-mar libreoffice-writer fonts-freefont-ttf \
      python3 python3-venv python3-pip acl jq curl git iptables util-linux procps unzip zip ca-certificates \
      sudo passwd diffutils findutils file xz-utils \
 && rm -rf /var/lib/apt/lists/*

# setup-python / setup-node install into the tool cache (same path as GitHub-hosted runners); kept across jobs.
# /home/runner: 750 as on GitHub-hosted runners (the base image makes it 777, which would let the sandbox user `engine`
# rename the runner's own files). /runner-state: the registration (named volume, see entrypoint.sh).
ENV RUNNER_TOOL_CACHE=/opt/hostedtoolcache \
    AGENT_TOOLSDIRECTORY=/opt/hostedtoolcache \
    ACTIONS_RUNNER_HOOK_JOB_STARTED=/opt/vps-runner/job-started.sh \
    ACTIONS_RUNNER_HOOK_JOB_COMPLETED=/opt/vps-runner/job-completed.sh
COPY entrypoint.sh cleanup.sh /opt/vps-runner/
RUN install -d -o runner -g runner -m 755 /opt/hostedtoolcache \
 && install -d -o runner -g runner -m 700 /runner-state \
 && chmod 750 /home/runner \
 && printf '#!/bin/bash\nexec /opt/vps-runner/cleanup.sh started\n' > /opt/vps-runner/job-started.sh \
 && printf '#!/bin/bash\nexec /opt/vps-runner/cleanup.sh completed\n' > /opt/vps-runner/job-completed.sh \
 && chown -R root:root /opt/vps-runner && chmod 755 /opt/vps-runner/*.sh

USER runner
WORKDIR /home/runner
ENTRYPOINT ["/opt/vps-runner/entrypoint.sh"]
