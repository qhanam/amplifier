# Makefile for sandbox environment management tool

.PHONY: help install test test-unit test-integration clean

help:
	@echo "Sandbox Environment Management - Available targets:"
	@echo "  make install           - Install dependencies"
	@echo "  make test              - Run all tests"
	@echo "  make test-unit         - Run unit tests only"
	@echo "  make test-integration  - Run integration tests only"
	@echo "  make clean             - Clean up test artifacts"

install:
	@echo "Installing dependencies..."
	uv sync

test: test-unit test-integration

test-unit:
	@echo "Running unit tests..."
	uv run pytest tests/ -v --ignore=tests/test_integration.py

test-integration:
	@echo "Running integration tests..."
	uv run pytest tests/test_integration.py -v

clean:
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
