# Caddy with the Layer-4 plugin required to proxy raw MQTT/TCP.
# The stock caddy image only provides HTTP reverse_proxy; MQTT is not HTTP.

# caddy-l4 v0.1.2 requires Go >= 1.25.1; use a current Caddy builder image.
FROM caddy:2.11.4-builder AS builder

RUN xcaddy build --with github.com/mholt/caddy-l4

FROM caddy:2.11.4-alpine

COPY --from=builder /usr/bin/caddy /usr/bin/caddy
