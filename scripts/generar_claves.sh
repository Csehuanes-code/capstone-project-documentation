#!/usr/bin/env sh
# Genera el par de claves ES256 (P-256) de Auth en ./secretos (ignorado por git).
# La PRIVADA solo la monta Auth; la PÚBLICA la montan los servicios que validan tokens.
set -e
# En Git Bash (Windows) evita que /out se convierta en una ruta de Windows.
export MSYS_NO_PATHCONV=1
cd "$(dirname "$0")/.."
mkdir -p secretos
if [ -f secretos/auth-es256.pem ]; then echo "Las claves ya existen en secretos/"; exit 0; fi
# 644: los servicios corren con un usuario sin privilegios y deben poder leerlas.
# En producción la privada va en un gestor de secretos, no en un archivo local.
docker run --rm -v "$(pwd)/secretos:/out" --entrypoint sh alpine/openssl -c \
  "openssl ecparam -name prime256v1 -genkey -noout -out /out/auth-es256.pem && openssl ec -in /out/auth-es256.pem -pubout -out /out/auth-es256-public.pem && chmod 644 /out/auth-es256.pem /out/auth-es256-public.pem"
echo "Claves creadas en secretos/"
