# TREND Dashboard - canonical container per plan D7.
# Base: rocker/r-ver:3.5.1 (matches Lib4_all_steps_FINAL_111525.sbatch:62 R version pin).
# Bioinformatics tools and Python layered on top.
#
# NOTE: This Dockerfile is the Week 5 deliverable. Week 1-4 dev runs natively via `make backend`
# and `make frontend`. Treat the layers below as the intended target; iterate in Week 5.

FROM rocker/r-ver:3.5.1

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# System packages: bioinformatics CLI tools + Python toolchain.
# Versions pinned to match the SBATCH where possible.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        curl \
        git \
        wget \
        unzip \
        bowtie2 \
        samtools \
        fastx-toolkit \
        cutadapt \
        python3 \
        python3-pip \
        python3-venv \
        libxml2-dev \
        libssl-dev \
        libcurl4-openssl-dev \
        zlib1g-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# R packages required by Step 8 + Step 9 scripts.
RUN R -e "install.packages(c('tidyverse', 'data.table', 'BiocManager'), repos='https://packagemanager.posit.co/cran/__linux__/$(lsb_release -cs)/latest')" \
 && R -e "BiocManager::install('Rsamtools', update=FALSE, ask=FALSE)"

# Frontend build tools (Node) for serving the static SPA.
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Backend: install dependencies first for layer caching.
COPY dashboard/pyproject.toml /app/dashboard/
RUN pip3 install --no-cache-dir -e /app/dashboard

# Frontend: install + build.
COPY dashboard/frontend/package.json dashboard/frontend/package-lock.json* /app/dashboard/frontend/
RUN cd /app/dashboard/frontend && npm ci || npm install

# Copy the rest of the dashboard + reference scripts/data needed at runtime.
COPY dashboard /app/dashboard
COPY codes /app/codes
COPY project_data /app/project_data

# Build frontend static bundle (served by FastAPI in production).
RUN cd /app/dashboard/frontend && npm run build

EXPOSE 8000

WORKDIR /app/dashboard

# First-launch ingest is idempotent; runs only if library.sqlite is missing/stale.
CMD ["sh", "-c", "make ingest && uvicorn backend.main:app --host 0.0.0.0 --port 8000"]
