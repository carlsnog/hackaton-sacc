.PHONY: image ingest pipeline serve test

IMAGE := vozes-ausentes-pb:dev

image:
	podman build -t $(IMAGE) .

ingest: image
	podman run --rm -v "$(CURDIR):/app:Z" $(IMAGE) python -m pipeline.ingest_sidra

pipeline: image
	podman run --rm -v "$(CURDIR):/app:Z" $(IMAGE) python -m pipeline.run_pipeline

serve: image
	podman run --rm -p 8000:8000 $(IMAGE)

test: image
	podman run --rm $(IMAGE) python -m unittest discover -s tests -v
