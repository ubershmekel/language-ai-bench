FROM python:3.11.11-slim-bookworm
WORKDIR /workspace
COPY solution/server.py ./src/server.py
EXPOSE 8080
CMD ["python", "src/server.py"]
