FROM python:3.11.11-slim-bookworm@sha256:081075da77b2b55c23c088251026fb69a7b2bf92471e491ff5fd75c192fd38e5
WORKDIR /workspace
COPY solution/config_merge.py ./src/config_merge.py
CMD ["python", "src/config_merge.py"]
