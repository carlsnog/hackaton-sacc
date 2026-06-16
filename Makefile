.PHONY: image ingest pipeline deploy-snapshot serve test

IMAGE := vozes-ausentes-pb:dev

CONTAINER_ENGINE := $(shell which podman 2>/dev/null || which docker 2>/dev/null)

image:
ifdef CONTAINER_ENGINE
	$(CONTAINER_ENGINE) build -t $(IMAGE) .
else
	@echo "Nenhum motor de container (podman/docker) encontrado. Executando localmente via virtualenv."
endif

ingest: image
ifdef CONTAINER_ENGINE
	$(CONTAINER_ENGINE) run --rm -v "$(CURDIR):/app:Z" $(IMAGE) python -m pipeline.ingest_sidra
else
	.venv/bin/python -m pipeline.ingest_sidra
endif

pipeline: image
ifdef CONTAINER_ENGINE
	$(CONTAINER_ENGINE) run --rm -v "$(CURDIR):/app:Z" $(IMAGE) python -m pipeline.run_pipeline
else
	.venv/bin/python -m pipeline.run_pipeline
endif

deploy-snapshot: image
ifdef CONTAINER_ENGINE
	$(CONTAINER_ENGINE) run --rm -v "$(CURDIR):/app:Z" $(IMAGE) python -m pipeline.publish_vercel_snapshot
else
	.venv/bin/python -m pipeline.publish_vercel_snapshot
endif

serve: image
ifdef CONTAINER_ENGINE
	$(CONTAINER_ENGINE) run --rm -p 8000:8000 $(IMAGE)
else
	.venv/bin/python -m app.main
endif

test: image
ifdef CONTAINER_ENGINE
	$(CONTAINER_ENGINE) run --rm $(IMAGE) python -m unittest discover -s tests -v
else
	.venv/bin/python -m unittest discover -s tests -v
endif
