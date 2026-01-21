.PHONY: build run-steps emit-runner run-runner

TAG ?= 0.1.2
IMAGE ?= localhost/ezansi-advisor:$(TAG)
CONTAINER_ENGINE ?= podman

# Absolute path to the blueprints repo checkout on the host.
BLUEPRINTS_DIR ?= /path/to/ezansi-blueprints

# Platform Core base URL.
PLATFORM ?= http://localhost:8000

# Blueprint path inside the container.
BLUEPRINT ?= /blueprints/blueprints/student-knowledge-rag.yml

# Where to write the generated runner script.
RUNNER_OUT ?= /tmp/run-blueprint.sh

build:
	cd . && $(CONTAINER_ENGINE) build -t $(IMAGE) -f Containerfile .

run-steps:
	$(CONTAINER_ENGINE) run --rm --network host \
		-v "$(BLUEPRINTS_DIR):/blueprints:ro" \
		$(IMAGE) \
		--platform $(PLATFORM) \
		--blueprint $(BLUEPRINT) \
		--print-steps

emit-runner:
	$(CONTAINER_ENGINE) run --rm --network host \
		-v "$(BLUEPRINTS_DIR):/blueprints:ro" \
		$(IMAGE) \
		--platform $(PLATFORM) \
		--blueprint $(BLUEPRINT) \
		--print-runner > $(RUNNER_OUT)

run-runner: emit-runner
	bash $(RUNNER_OUT)
