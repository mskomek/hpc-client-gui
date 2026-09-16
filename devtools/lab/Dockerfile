# Local single-node HPC lab: real OpenSSH + real SFTP subsystem + real Slurm
# (slurmdbd/slurmctld/slurmd) so integration Waves can be proven against a
# genuine SSH/SFTP/Slurm stack instead of mocks.
#
# This image is a DISPOSABLE TEST FIXTURE. Its credentials are fixed, public
# and test-only; never reuse them anywhere else and never expose the container
# outside localhost.
FROM debian:trixie-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        openssh-server \
        slurm-wlm \
        slurmdbd \
        munge \
        mariadb-server \
        ca-certificates \
        procps \
        iproute2 \
        vim-tiny \
        less \
        locales \
    && sed -i 's/^# *\(en_US.UTF-8\|tr_TR.UTF-8\)/\1/' /etc/locale.gen \
    && locale-gen \
    && rm -rf /var/lib/apt/lists/*

ENV LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8

# --- test account -----------------------------------------------------------
# Password auth keeps the lab usable by every client path the app supports
# (password, and key auth once you drop a key into ~/.ssh/authorized_keys).
ARG LAB_USER=hpctest
ARG LAB_PASSWORD=hpctest
RUN useradd --create-home --shell /bin/bash "${LAB_USER}" \
    && echo "${LAB_USER}:${LAB_PASSWORD}" | chpasswd \
    && mkdir -p /home/${LAB_USER}/.ssh \
    && chmod 700 /home/${LAB_USER}/.ssh \
    && chown -R ${LAB_USER}:${LAB_USER} /home/${LAB_USER}/.ssh

# Provider-shaped paths so a TRUBA-like cluster profile resolves without
# inventing site-specific settings in the client.
RUN mkdir -p /arf/home/${LAB_USER} /arf/scratch/${LAB_USER} \
    && chown -R ${LAB_USER}:${LAB_USER} /arf

# --- sshd -------------------------------------------------------------------
RUN mkdir -p /run/sshd \
    && sed -i 's/^#\?PasswordAuthentication .*/PasswordAuthentication yes/' /etc/ssh/sshd_config \
    && sed -i 's/^#\?PermitRootLogin .*/PermitRootLogin no/' /etc/ssh/sshd_config \
    && sed -i 's/^#\?Subsystem\s\+sftp.*/Subsystem sftp internal-sftp/' /etc/ssh/sshd_config \
    && printf '\nAcceptEnv LANG LC_*\nX11Forwarding yes\nPrintMotd no\n' >> /etc/ssh/sshd_config

# --- slurm dirs -------------------------------------------------------------
RUN mkdir -p /var/spool/slurmctld /var/spool/slurmd /var/log/slurm /run/munge \
    && chown -R slurm:slurm /var/spool/slurmctld /var/log/slurm \
    && chmod 755 /var/spool/slurmd

COPY slurm.conf /etc/slurm/slurm.conf
COPY cgroup.conf /etc/slurm/cgroup.conf
COPY slurmdbd.conf /etc/slurm/slurmdbd.conf
COPY entrypoint.sh /usr/local/bin/entrypoint.sh

RUN chmod 0644 /etc/slurm/slurm.conf /etc/slurm/cgroup.conf \
    && chown slurm:slurm /etc/slurm/slurmdbd.conf \
    && chmod 0600 /etc/slurm/slurmdbd.conf \
    && chmod 0755 /usr/local/bin/entrypoint.sh

EXPOSE 22
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
