# Caddy with the Layer-4 plugin required to proxy raw MQTT/TCP.
# The stock caddy image only provides HTTP reverse_proxy; MQTT is not HTTP.

FROM caddy:2.8-builder AS builder

RUN xcaddy build --with github.com/mholt/caddy-l4

FROM caddy:2.8-alpine

COPY --from=builder /usr/bin/caddy /usr/bin/caddy
