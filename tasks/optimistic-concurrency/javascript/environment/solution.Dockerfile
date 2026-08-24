FROM node:22.14.0-bookworm-slim
WORKDIR /workspace
COPY solution/server.js ./src/server.js
EXPOSE 8080
CMD ["node", "src/server.js"]
