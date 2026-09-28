#!/bin/bash
set -e

echo "=== 1. Baixando alterações do Git (origin master) ==="
git pull origin master

echo "=== 2. Reconstruindo a imagem da aplicação (sem cache) ==="
DOCKER_BUILDKIT=0 docker compose -f compose.yaml build --no-cache app

echo "=== 3. Atualizando o container da aplicação ==="
docker compose -f compose.yaml up -d --no-deps app

echo "=== Deploy concluído com sucesso! ==="