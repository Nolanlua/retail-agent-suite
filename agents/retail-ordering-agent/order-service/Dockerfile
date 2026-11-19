FROM golang:1.23-alpine AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/order-service ./cmd/order-service

FROM gcr.io/distroless/static-debian12
COPY --from=build /out/order-service /order-service
EXPOSE 8020
ENTRYPOINT ["/order-service"]
