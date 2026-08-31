FROM python:3.11.11-slim-bookworm@sha256:081075da77b2b55c23c088251026fb69a7b2bf92471e491ff5fd75c192fd38e5
WORKDIR /workspace
COPY solution/main.py solution/parse.py solution/redact.py ./src/
CMD ["python", "src/main.py"]
