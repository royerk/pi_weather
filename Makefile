-include .env

PYTHON := python
SQLITE := sqlite3
APT_INSTALL := sudo apt install -y
ifeq ($(IN_DOCKER),)
	APT_INSTALL := apt install -y
	PYTHON := python3
endif

clean:
	rm -rf venv; \
	@echo "Virtual environment removed."; \
	docker rmi pi-weather; \
	@echo "Docker image removed."; \

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

setup-server-local:
	$(APT_INSTALL) sqlite3; \
	$(PYTHON) -m pip install -r requirements-server.txt; \
	$(PYTHON) pi_weather/app/db_utils.py; \

run-server-local: setup-server-local
	$(PYTHON) pi_weather/app/app.py; \

docker-build:
	docker build -t pi-weather .; \

docker-run: docker-build
	docker run --rm -p 5000:5000 --name test-pi-weather pi-weather; \

test: docker-build venv
	. venv/bin/activate; \
	pytest; \

safe-delete-server-remote:
	ssh $(REMOTE_USER)@$(REMOTE_HOST) \
		'TIMESTAMP=$$(date "+%Y%m%d_%H%M%S"); \
		cp $(REMOTE_PATH)/pi-weather/data.db $(REMOTE_PATH)/data_$$TIMESTAMP.db; \
		rm -rf $(REMOTE_PATH)/pi-weather'

make-tar:
	git ls-files -z | tar -czf code.tar.gz --null -T -

remove-tar:
	rm code.tar.gz

deploy-server-remote: make-tar
    scp code.tar.gz $(REMOTE_USER)@$(REMOTE_HOST):$(REMOTE_PATH); \
	remove-tar; \
    ssh $(REMOTE_USER)@$(REMOTE_HOST) \
		"mkdir -p $(REMOTE_PATH)/pi-weather; \
		tar -xzf $(REMOTE_PATH)/code.tar.gz -C $(REMOTE_PATH)/pi-weather && rm $(REMOTE_PATH)/code.tar.gz"; \

setup-server-remote:
	ssh $(REMOTE_USER)@$(REMOTE_HOST) \
		"sudo apt update; sudo apt install -y python3-pip python3-venv sqlite3; \
		cd $(REMOTE_PATH)/pi-weather; \
		python3 -m venv venv; source venv/bin/activate && pip install -r requirements-server.txt; \
		python3 pi_weather/app/db_utils.py"

run-server-remote:
	ssh $(REMOTE_USER)@$(REMOTE_HOST) \
		"nohup $(REMOTE_PATH)/pi-weather/venv/bin/python3 $(REMOTE_PATH)/pi-weather/pi_weather/app/app.py  >/dev/null 2>/dev/null </dev/null  &"

stop-server-remote:
	ssh $(REMOTE_USER)@$(REMOTE_HOST) \
		"pkill -f 'python3 pi_weather/app/app.py'"

deploy-sensor-1: make-tar
	scp code.tar.gz $(REMOTE_USER)@$(REMOTE_HOST_SENSOR_1):$(REMOTE_PATH); \
	ssh $(REMOTE_USER)@$(REMOTE_HOST_SENSOR_1) \
		"mkdir -p $(REMOTE_PATH)/pi-weather; \
		tar -xzf $(REMOTE_PATH)/code.tar.gz -C $(REMOTE_PATH)/pi-weather && rm $(REMOTE_PATH)/code.tar.gz; \
		cd $(REMOTE_PATH)/pi-weather; \
		python3 -m venv venv; source venv/bin/activate && pip install -r requirements-sensor.txt; \
		git clone https://github.com/pimoroni/bmp280-python; sudo bmp280-python/install.sh;"; \
	remove-tar; \
	# TODO add cron job to run sensor