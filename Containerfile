FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN python -m pipeline.run_pipeline
EXPOSE 8000
CMD ["python", "-m", "app.main"]
