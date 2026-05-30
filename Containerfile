FROM python:3.12-slim

WORKDIR /app

# Instalar dependências necessárias para a Web App, IA e scripts de análise
RUN pip install --no-cache-dir pandas requests openai fastapi uvicorn

COPY . .

# Executa o pipeline de ingestão do IBGE/SIDRA
RUN python -m pipeline.run_pipeline

EXPOSE 8000

# Por padrão, inicia o servidor da aplicação web
CMD ["python", "-m", "app.main"]

