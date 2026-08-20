FROM ubuntu:24.04

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
       libegl1 \
       libgl1 \
       libxkbcommon0 \
       libxcb-xinerama0 \
       python3 \
       python3-venv \
       wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /work
