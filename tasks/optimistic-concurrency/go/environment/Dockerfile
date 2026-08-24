FROM golang:1.24.0-bookworm AS build
WORKDIR /src
COPY . .
RUN go build -o /server ./src
FROM debian:bookworm-slim
COPY --from=build /server /server
EXPOSE 8080
CMD ["/server"]

