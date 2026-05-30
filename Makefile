.PHONY: image pipeline serve test

IMAGE := vozes-ausentes-pb:dev

image:
	podman build -t $(IMAGE) .

pipeline: image
	podman run --rm -v "$(CURDIR):/app:Z" $(IMAGE) python -m pipeline.run_pipeline

serve: image
	podman run --rm -p 8000:8000 $(IMAGE)

test: image
	podman run --rm $(IMAGE) python -m unittest discover -s tests -v
