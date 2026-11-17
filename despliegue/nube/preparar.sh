#!/bin/sh
# Prepara la VM para docker-compose.nube.yml. Se ejecuta una vez desde la raíz del repo:
#   sh despliegue/nube/preparar.sh 20-226-88-58.sslip.io
# Crea claves ES256 nuevas, un .env con contraseñas aleatorias y la ruta protegida de Mailpit.
set -e
DOMINIO="${1:?uso: sh despliegue/nube/preparar.sh <dominio>}"
cd "$(dirname "$0")/../.."

if [ ! -f secretos/auth-es256.pem ]; then sh scripts/generar_claves.sh; fi

if [ ! -f .env ]; then
  printf 'DOMINIO=%s\nURL_PUBLICA=https://%s\nADMIN_PASSWORD=Admin-%s\nCORREO_PASSWORD=%s\n' \
    "$DOMINIO" "$DOMINIO" "$(openssl rand -hex 6)" "$(openssl rand -hex 6)" > .env
  chmod 600 .env
fi
. ./.env

HASH=$(openssl passwd -apr1 "$CORREO_PASSWORD")
cat > despliegue/nube/correo.yml <<EOF
# Generado por preparar.sh: Mailpit en /correo con basic auth (usuario "equipo").
http:
  routers:
    correo:
      rule: "PathPrefix(\`/correo\`)"
      service: correo
      priority: 200
      middlewares: [correo-auth]
  middlewares:
    correo-auth:
      basicAuth:
        users: ["equipo:$HASH"]
  services:
    correo:
      loadBalancer:
        servers: [{ url: "http://mailpit:8025" }]
EOF

echo "Listo. Admin: admin@turismo.co / $ADMIN_PASSWORD · Correos: https://$DOMINIO/correo/ (equipo / $CORREO_PASSWORD)"
