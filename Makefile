# HawkFish Makefile
# Provides automation for development, testing, and release processes

.PHONY: help install dev-install test lint format clean build docker helm-* chart-*

# Configuration
PYTHON := python3
PIP := pip3
HELM := helm
DOCKER := docker
CHART_DIR := charts/hawkfish
CHART_NAME := hawkfish
VERSION ?= $(shell grep '^version' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
DOCKER_REGISTRY ?= ghcr.io
DOCKER_REPO ?= $(DOCKER_REGISTRY)/$(shell git config --get remote.origin.url | sed 's/.*[:/]\([^/]*\)\/\([^/]*\)\.git/\1\/\2/' | tr '[:upper:]' '[:lower:]')

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

## Display this help message
help:
	@echo "$(BLUE)HawkFish Development Makefile$(NC)"
	@echo ""
	@echo "$(YELLOW)Available targets:$(NC)"
	@awk '/^##/{c=substr($$0,3);next}c&&/^[[:alpha:]][[:alnum:]_-]+:/{print substr($$1,1,index($$1,":")-1)":"c}1{c=""}' $(MAKEFILE_LIST) | column -t -s ':' | sed 's/^/  /'
	@echo ""

## Install production dependencies
install:
	@echo "$(GREEN)Installing production dependencies...$(NC)"
	$(PIP) install -e .

## Install development dependencies
dev-install:
	@echo "$(GREEN)Installing development dependencies...$(NC)"
	$(PIP) install -e .[dev]
	@echo "$(GREEN)Installing pre-commit hooks...$(NC)"
	pre-commit install

## Run all tests
test:
	@echo "$(GREEN)Running tests...$(NC)"
	pytest tests/ -v --tb=short

## Run unit tests only
test-unit:
	@echo "$(GREEN)Running unit tests...$(NC)"
	pytest tests/unit/ -v --tb=short

## Run integration tests only
test-integration:
	@echo "$(GREEN)Running integration tests...$(NC)"
	pytest tests/integration/ -v --tb=short

## Run linting checks
lint:
	@echo "$(GREEN)Running linting checks...$(NC)"
	ruff check .
	mypy src

## Fix linting issues automatically
lint-fix:
	@echo "$(GREEN)Fixing linting issues...$(NC)"
	ruff check . --fix
	ruff format .

## Format code
format:
	@echo "$(GREEN)Formatting code...$(NC)"
	ruff format .

## Clean build artifacts
clean:
	@echo "$(GREEN)Cleaning build artifacts...$(NC)"
	rm -rf build/ dist/ *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache/
	rm -rf .coverage htmlcov/
	rm -rf packaged-charts/

## Build Python package
build: clean
	@echo "$(GREEN)Building Python package...$(NC)"
	$(PYTHON) -m build

## Build Docker image
docker-build:
	@echo "$(GREEN)Building Docker image...$(NC)"
	$(DOCKER) build -t $(DOCKER_REPO)/$(CHART_NAME):$(VERSION) \
		--build-arg VERSION=$(VERSION) \
		--label "org.opencontainers.image.version=$(VERSION)" \
		--label "org.opencontainers.image.created=$(shell date -u +%Y-%m-%dT%H:%M:%SZ)" \
		.

## Push Docker image
docker-push: docker-build
	@echo "$(GREEN)Pushing Docker image...$(NC)"
	$(DOCKER) push $(DOCKER_REPO)/$(CHART_NAME):$(VERSION)
	$(DOCKER) tag $(DOCKER_REPO)/$(CHART_NAME):$(VERSION) $(DOCKER_REPO)/$(CHART_NAME):latest
	$(DOCKER) push $(DOCKER_REPO)/$(CHART_NAME):latest

## Validate Helm charts
helm-lint:
	@echo "$(GREEN)Linting Helm charts...$(NC)"
	@for chart in charts/*/; do \
		chart_name=$$(basename $$chart); \
		echo "$(BLUE)Linting $$chart_name...$(NC)"; \
		$(HELM) lint $$chart; \
	done

## Test Helm chart templates
helm-template:
	@echo "$(GREEN)Testing Helm chart templates...$(NC)"
	@for chart in charts/*/; do \
		chart_name=$$(basename $$chart); \
		echo "$(BLUE)Testing templates for $$chart_name...$(NC)"; \
		$(HELM) template test $$chart --debug --dry-run > /dev/null; \
	done

## Package Helm charts
helm-package: helm-lint
	@echo "$(GREEN)Packaging Helm charts...$(NC)"
	@mkdir -p packaged-charts
	@for chart in charts/*/; do \
		chart_name=$$(basename $$chart); \
		echo "$(BLUE)Packaging $$chart_name...$(NC)"; \
		$(HELM) package $$chart --destination packaged-charts/; \
	done

## Update Helm chart dependencies
helm-deps:
	@echo "$(GREEN)Updating Helm chart dependencies...$(NC)"
	@for chart in charts/*/; do \
		if [ -f "$$chart/Chart.yaml" ] && grep -q "^dependencies:" "$$chart/Chart.yaml"; then \
			chart_name=$$(basename $$chart); \
			echo "$(BLUE)Updating dependencies for $$chart_name...$(NC)"; \
			$(HELM) dependency update $$chart; \
		fi; \
	done

## Generate Helm chart documentation
helm-docs:
	@echo "$(GREEN)Generating Helm chart documentation...$(NC)"
	@if command -v helm-docs >/dev/null 2>&1; then \
		helm-docs charts/; \
	else \
		echo "$(YELLOW)helm-docs not installed. Install with: go install github.com/norwoodj/helm-docs/cmd/helm-docs@latest$(NC)"; \
	fi

## Update chart versions to match project version
chart-version-update:
	@echo "$(GREEN)Updating chart versions to $(VERSION)...$(NC)"
	@for chart in charts/*/Chart.yaml; do \
		chart_name=$$(basename $$(dirname $$chart)); \
		echo "$(BLUE)Updating $$chart_name to version $(VERSION)...$(NC)"; \
		sed -i "s/^version: .*/version: $(VERSION)/" $$chart; \
		sed -i "s/^appVersion: .*/appVersion: \"$(VERSION)\"/" $$chart; \
	done

## Generate CRDs (Custom Resource Definitions) if needed
chart-crds-generate:
	@echo "$(GREEN)Generating CRDs...$(NC)"
	@# Add CRD generation logic here if your project uses Kubernetes CRDs
	@# Example: controller-gen crd paths=./api/... output:crd:artifacts:config=charts/hawkfish/crds
	@echo "$(YELLOW)No CRDs to generate for this project$(NC)"

## Update chart templates with latest configurations
chart-templates-update:
	@echo "$(GREEN)Updating chart templates...$(NC)"
	@# Update any generated templates or configurations
	@$(MAKE) chart-version-update
	@$(MAKE) chart-crds-generate

## Full chart preparation for release
chart-prepare-release: chart-templates-update helm-deps helm-lint helm-template
	@echo "$(GREEN)Charts prepared for release $(VERSION)$(NC)"

## Install chart locally for testing
chart-install-local: helm-package
	@echo "$(GREEN)Installing chart locally for testing...$(NC)"
	$(HELM) upgrade --install $(CHART_NAME)-test packaged-charts/$(CHART_NAME)-$(VERSION).tgz \
		--namespace hawkfish-test --create-namespace \
		--set image.tag=$(VERSION) \
		--wait --timeout=300s

## Uninstall local test chart
chart-uninstall-local:
	@echo "$(GREEN)Uninstalling local test chart...$(NC)"
	$(HELM) uninstall $(CHART_NAME)-test --namespace hawkfish-test || true
	kubectl delete namespace hawkfish-test || true

## Run chart tests
chart-test: chart-install-local
	@echo "$(GREEN)Running chart tests...$(NC)"
	$(HELM) test $(CHART_NAME)-test --namespace hawkfish-test

## Full development setup
dev-setup: dev-install helm-deps
	@echo "$(GREEN)Development environment setup complete!$(NC)"

## Full release preparation
release-prepare: clean build docker-build chart-prepare-release helm-package
	@echo "$(GREEN)Release $(VERSION) prepared successfully!$(NC)"
	@echo "$(BLUE)Next steps:$(NC)"
	@echo "  1. Review packaged-charts/ directory"
	@echo "  2. Test Docker image: $(DOCKER_REPO)/$(CHART_NAME):$(VERSION)"
	@echo "  3. Create git tag: git tag v$(VERSION)"
	@echo "  4. Push tag: git push origin v$(VERSION)"

## Show current version
version:
	@echo "$(GREEN)Current version: $(VERSION)$(NC)"

## Show project status
status:
	@echo "$(BLUE)HawkFish Project Status$(NC)"
	@echo "Version: $(VERSION)"
	@echo "Charts directory: $(CHART_DIR)"
	@echo "Docker repository: $(DOCKER_REPO)"
	@echo ""
	@echo "$(YELLOW)Available charts:$(NC)"
	@ls -la charts/ 2>/dev/null || echo "No charts directory found"
	@echo ""
	@echo "$(YELLOW)Recent packaged charts:$(NC)"
	@ls -la packaged-charts/ 2>/dev/null || echo "No packaged charts found"