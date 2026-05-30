#!/bin/bash
# Garantir que o script mude para seu próprio diretório
cd "$(dirname "$0")"

IMAGE_NAME="hackaton-tse"

# 1. Construir a imagem Podman se necessário (ou atualizar)
echo "📦 [Podman] Construindo/Verificando imagem '$IMAGE_NAME'..."
podman build -t "$IMAGE_NAME" -f Containerfile .

# 2. Verificar se o usuário quer rodar algum script específico
SCRIPT_TO_RUN="geral_eleitores_pb.py"
if [ "$#" -gt 0 ]; then
  # Se passou argumentos, usa o primeiro como script e repassa os demais
  SCRIPT_TO_RUN="$1"
  shift
fi

echo "🚀 [Podman] Executando o script '$SCRIPT_TO_RUN' no container isolado..."
echo "------------------------------------------------------------------------"

# Adiciona mapeamento de porta apenas se for rodar o servidor web da aplicação
PORT_MAPPING=""
if [[ "$SCRIPT_TO_RUN" == *"app.main"* || "$*" == *"app.main"* || "$SCRIPT_TO_RUN" == "serve" ]]; then
  PORT_MAPPING="-p 8000:8000"
fi


# Executar o container mapeando a pasta atual e passando variáveis de ambiente
podman run --rm -it \
  -v "$(pwd):/app:Z" \
  $PORT_MAPPING \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  "$IMAGE_NAME" python3 "$SCRIPT_TO_RUN" "$@"


