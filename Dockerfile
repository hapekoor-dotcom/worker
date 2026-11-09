FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04
ARG BLENDER_VERSION=4.5.9
ENV PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl xz-utils python3-pip libgl1 libx11-6 libxfixes3 \
    libxi6 libxrender1 libxkbcommon0 libsm6 libgomp1 libglu1-mesa \
    && rm -rf /var/lib/apt/lists/*
RUN mkdir -p /opt/blender && curl -fSL --retry 3 \
    "https://download.blender.org/release/Blender4.5/blender-${BLENDER_VERSION}-linux-x64.tar.xz" \
    | tar -xJ -C /opt/blender --strip-components=1
RUN python3 -m pip install --no-cache-dir runpod==1.8.1
WORKDIR /app
COPY handler.py render.py ./
CMD ["python3", "-u", "handler.py"]
