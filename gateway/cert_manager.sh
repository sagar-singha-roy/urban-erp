#!/bin/sh
# Requests a certificate for each domain core-service lists, and renews what is due.
DOMAINS=/etc/nginx/urban/generated/live/acme-domains.txt

while true; do
  if [ -n "$ACME_EMAIL" ] && [ -f "$DOMAINS" ]; then
    while read -r domain; do
      [ -n "$domain" ] || continue
      certbot certonly --webroot -w /var/www/acme -d "$domain" --non-interactive --agree-tos -m "$ACME_EMAIL" --keep-until-expiring \
        || echo "Certificate request failed for $domain"
    done < "$DOMAINS"
    certbot renew --non-interactive --webroot -w /var/www/acme || echo "Certificate renewal failed"
  fi
  sleep 3600
done
