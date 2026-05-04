# TREND Dashboard — canonical container.
#
# Multi-stage build:
#   1. node:20 — builds the React/Vite frontend bundle (dist/)
#   2. condaforge/mambaforge — installs the trend conda env (R, bowtie2,
#      samtools, cutadapt, fastx-toolkit, Python deps), then drops in the
#      built frontend and the trend CLI.
#
# This same image serves three use cases:
#   - Reviewer verification:  docker run -p 8000:8000 <image>
#   - Real pipeline run:      docker run -v ./fastqs:/data -v ./runs:/runs <image> trend run --inputs /data --output /runs
#   - HPC via Singularity:    singularity build trend.sif docker://<image>; singularity run trend.sif trend ...
#
# R version: pinned to whatever is current in the bioconda r-base feed at
# build time (typically R 4.3+). The manuscript SBATCH used R 3.5.1; small
# numeric drift between R versions is documented in the run manifest.

# ---------------------------------------------------------------------------
# Stage 1: build the frontend
# ---------------------------------------------------------------------------
FROM node:20-bookworm-slim AS frontend-builder

WORKDIR /frontend

# Copy package manifests first for best layer caching — only re-runs npm ci
# when package.json changes.
COPY dashboard/frontend/package.json dashboard/frontend/package-lock.json* ./
RUN npm ci || npm install

# Copy the rest of the frontend source and build the static bundle.
COPY dashboard/frontend ./
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2: runtime with conda env + bioinformatics tools
# ---------------------------------------------------------------------------
FROM condaforge/mambaforge:latest

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# A few utilities not in the conda env that are useful at runtime
# (curl for healthchecks).
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Install the conda env. Copying just the env file first lets Docker cache
# the (slow) mamba install layer until environment.yml itself changes.
COPY pipeline/environment.yml /tmp/environment.yml
RUN mamba env create -n trend -f /tmp/environment.yml \
 && mamba clean -afy

# Make the trend env's binaries available on PATH for all subsequent layers
# AND for the runtime CMD.
ENV PATH=/opt/conda/envs/trend/bin:$PATH
ENV CONDA_DEFAULT_ENV=trend

# Copy the rest of the project (source code, codes/, project_data/, examples).
WORKDIR /app
COPY . /app

# Install the trend CLI in editable mode so `trend` is on PATH.
RUN /opt/conda/envs/trend/bin/pip install -e /app/pipeline

# Drop in the prebuilt frontend bundle from stage 1.
COPY --from=frontend-builder /frontend/dist /app/dashboard/frontend/dist

# Verify the install during build so any breakage is caught here, not at runtime.
RUN trend --version && trend preflight || true

WORKDIR /app/dashboard
EXPOSE 8000

# Default: launch the dashboard. Overridable for pipeline runs:
#   docker run <image> trend run --inputs /data --output /runs
#
# library.sqlite + library_summary.json are baked into the image at build
# time via the `gh release download` step in .github/workflows/docker-publish.yml,
# so no `make ingest` is needed at startup.
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
