FROM node:22.14.0-bookworm-slim
WORKDIR /workspace
COPY package*.json tsconfig.json ./
RUN npm ci
COPY . .
RUN npm run build
EXPOSE 8080
CMD ["node", "dist/server.js"]

