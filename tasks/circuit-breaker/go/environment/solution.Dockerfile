FROM golang:1.24.0-bookworm@sha256:b970e6d47c09fdd34179acef5c4fecaf6410f0b597a759733b3cbea04b4e604a
WORKDIR /workspace
COPY go.mod ./
COPY solution/breaker.go solution/main.go solution/parse.go ./src/
RUN go build -o /circuit-breaker ./src
CMD ["/circuit-breaker"]
