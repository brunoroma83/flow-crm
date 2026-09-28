# 1. Baixa o código atualizado
git pull origin main

# 2. Reconstrói apenas a imagem da aplicação (sem alterar o banco de dados)
docker compose -f compose.yaml build app

# 3. Recria o container da aplicação de forma rápida (sem reiniciar o postgres)
docker compose -f compose.yaml up -d --no-deps app