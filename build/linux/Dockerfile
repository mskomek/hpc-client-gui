FROM ubuntu:26.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates \
       dpkg-dev \
       file \
       flatpak \
       flatpak-builder \
       fuse3 \
       libfuse2t64 \
       libasound2t64 \
       libatk1.0-0t64 \
       libcups2t64 \
       libegl1 \
       libgl1 \
       libgtk-3-0t64 \
       libnspr4 \
       libnss3 \
       libpulse0 \
       libxcomposite1 \
       libxdamage1 \
       libxfixes3 \
       libxkbcommon0 \
       libxkbcommon-x11-0 \
       libxkbfile1 \
       libxrandr2 \
       libxtst6 \
       libxcb-cursor0 \
       libxcb-icccm4 \
       libxcb-image0 \
       libxcb-keysyms1 \
       libxcb-render-util0 \
       libxcb-shape0 \
       libxcb-util1 \
       libxcb-xinerama0 \
       libxcb-xkb1 \
       python3 \
       libpython3.14 \
       python3-venv \
       wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /work
