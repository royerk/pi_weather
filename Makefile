PYTHON := python
SQLITE := sqlite3
APT_INSTALL := sudo apt install -y
ifeq ($(IN_DOCKER),)
	APT_INSTALL := apt install -y
	PYTHON := python3
endif


clean:
	rm -rf venv; \
	echo "Virtual environment removed."; \
	docker rmi pi-weather; \
	echo "Docker image removed."; \

venv:
	@if [ -d venv ]; then \
		echo "Virtual environment exists"; \
	else \
		echo "Creating new virtual environment..."; \
		$(PYTHON) -m venv venv; \
		echo "Virtual environment created."; \
		echo "Updating virtual environment..."; \
		. venv/bin/activate && pip -V; \
		$(PYTHON) -m pip install --upgrade pip; \
		$(PYTHON) -m pip install -r requirements-dev.txt; \
		echo "Virtual environment updated."; \
	fi; \

lint: venv
	. venv/bin/activate; \
	isort --profile black .; \
	black .; \
	mdformat .; \

setup-server:
	$(APT_INSTALL) sqlite3; \
	$(PYTHON) -m pip install -r requirements-server.txt; \
	$(PYTHON) pi_weather/app/db_utils.py; \

run-server: setup-server
	$(PYTHON) pi_weather/app/app.py; \

docker-build:
	docker build -t pi-weather .; \

docker-run: docker-build
	docker run --rm -p 5000:5000 pi-weather; \

test: docker-build venv
	. venv/bin/activate; \
	pytest; \

setup-sensor:
	$(PYTHON) -m pip install -r requirements-sensor.txt; \
