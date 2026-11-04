# Start from the official Airflow image (pinned version, like postgres:16)
FROM apache/airflow:3.3.2

# LightGBM needs the OpenMP library, which isn't in the base image.
# Installing system packages needs root, then we go back to the normal user.
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*
USER airflow

# Our pipeline's libraries, in their own virtual environment,
# so they never clash with Airflow's own libraries.
COPY airflow/requirements-pipeline.txt /tmp/requirements-pipeline.txt
RUN python -m venv /home/airflow/velib_venv \
    && /home/airflow/velib_venv/bin/pip install --no-cache-dir -r /tmp/requirements-pipeline.txt