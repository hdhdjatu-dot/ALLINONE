
FROM python:3.12-slim

# ============================================================
# SYSTEM DEPENDENCIES
# ============================================================

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ffmpeg \
       libopus0 \
       curl \
       unzip \
       ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# ============================================================
# INSTALL DENO
# ============================================================

RUN curl -fsSL https://deno.land/install.sh | sh

ENV DENO_INSTALL=/root/.deno
ENV PATH="/root/.deno/bin:${PATH}"

# Verify Deno is actually available inside the container
RUN deno --version

# ============================================================
# APPLICATION
# ============================================================

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

# ============================================================
# START BOT
# ============================================================

CMD ["python", "main.py"]

