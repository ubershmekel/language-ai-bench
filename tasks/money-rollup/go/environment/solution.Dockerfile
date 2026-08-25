FROM golang:1.24.0-bookworm@sha256:b970e6d47c09fdd34179acef5c4fecaf6410f0b597a759733b3cbea04b4e604a
WORKDIR /workspace
COPY go.mod ./
COPY solution/fx.go solution/main.go solution/money.go solution/rollup.go ./src/
RUN go build -o /money-rollup ./src
CMD ["/money-rollup"]
