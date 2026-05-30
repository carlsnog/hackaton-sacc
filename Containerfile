FROM python:3.10-slim

WORKDIR /app

# Instalar dependências necessárias para os scripts
RUN pip install --no-cache-dir pandas requests openai

# Por padrão, executa a análise demográfica geral
CMD ["python3", "geral_eleitores_pb.py"]
