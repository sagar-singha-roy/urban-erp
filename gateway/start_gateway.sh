#!/bin/sh
# Starts NGINX, then applies new host configuration as core-service writes it.
CONF=/etc/nginx/urban/nginx.docker.conf
GENERATED=/etc/nginx/urban/generated
mkdir -p "$GENERATED/live/certs"
[ -f "$GENERATED/live/sites.conf" ] || : > "$GENERATED/live/sites.conf"

nginx -g "daemon off;" -c "$CONF" &
NGINX_PID=$!

while kill -0 "$NGINX_PID" 2>/dev/null; do
  sleep 10
  sh /etc/nginx/urban/apply_generated.sh "$GENERATED" "nginx -t -c $CONF" "nginx -s reload -c $CONF"
done
