-include .env

PYTHON := python
SQLITE := sqlite3
APT_INSTALL := sudo apt install -y
ifeq ($(IN_DOCKER),)
	APT_INSTALL := apt install -y
	PYTHON := python3
endif

clean:
	@rm -rf venv
	@echo "Virtual environment removed."

	@docker rmi pi-weather
	@echo "Docker image removed."

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
	@echo "Building docker image..."
	@docker build -t pi-weather .
	@echo "Docker image built successfully."

local-data:
	@bash scripts/generate_local_fake_data.sh

docker-launch: docker-build
	@echo "Running docker container..."
	@docker run --rm -d -p 5000:5000 --name test-pi-weather pi-weather
	@sleep 4

docker-attach:
	@docker exec -it test-pi-weather /bin/bash

docker-kill:
	@echo "Stopping docker container..."
	@docker kill test-pi-weather

docker-run: docker-build docker-launch local-data

test: docker-build venv
	. venv/bin/activate; \
	pytest; \

safe-delete-server-remote:
	@echo "Backing up database ($(REMOTE_PATH)/weather_data.db)..."
	@ssh $(REMOTE_USER)@$(REMOTE_HOST) \
		'if [ -f $(REMOTE_PATH)/weather_data.db ]; then \
			TIMESTAMP=$(date "+%Y%m%d_%H%M%S"); \
			cp $(REMOTE_PATH)/weather_data.db $(REMOTE_PATH)/weather_data_$${TIMESTAMP}.db; \
		fi'
	@echo "Database backed up successfully (if there was one)."

	@echo "Removing code..."
	@ssh $(REMOTE_USER)@$(REMOTE_HOST) \
		"rm -rf $(REMOTE_PATH)/pi-weather"
	@echo "Code removed successfully."

	@echo "Removing cronjobs..."
	@ssh $(REMOTE_USER)@$(REMOTE_HOST) \
		"crontab -l | grep -v '*pi_weather/app*' | crontab -"
	@echo "Cronjobs removed successfully."

make-tar:
	@git ls-files -z | tar -czf code.tar.gz --null -T -
	@echo "Code tarball created."

remove-tar:
	@rm code.tar.gz
	@echo "Code tarball removed."

.PHONY: deploy-server-remote
deploy-server-remote:
	@echo "Deploying code tarball to remote server..."
	@scp code.tar.gz $(REMOTE_USER)@$(REMOTE_HOST):$(REMOTE_PATH)
	@echo "Code tarball copied to remote server."

	@echo "Deploying code on remote server..."
	@ssh $(REMOTE_USER)@$(REMOTE_HOST) \
		"rm -rf $(REMOTE_PATH)/pi-weather/pi_weather/app; \
		rm -rf $(REMOTE_PATH)/pi-weather/venv; \
		rm ${REMOTE_PATH}/pi-weather/requirements-server.txt; \
		\
		mkdir -p $(REMOTE_PATH)/pi-weather; \
		tar -xzf $(REMOTE_PATH)/code.tar.gz -C $(REMOTE_PATH)/pi-weather && rm $(REMOTE_PATH)/code.tar.gz"
	@echo "Code deployed successfully."
	@touch .last_deploy_server

deploy: make-tar deploy-server-remote remove-tar

setup-server-remote:
	@echo "Setting up server on remote..."
	@ssh $(REMOTE_USER)@$(REMOTE_HOST) \
		"sudo apt update; sudo apt install -y python3-pip python3-venv sqlite3 libopenblas-base; \
		cd $(REMOTE_PATH)/pi-weather; \
		python3 -m venv venv; source venv/bin/activate && pip install -r requirements-server.txt; \
		python3 pi_weather/app/db_utils.py"
	@echo "Server setup on remote completed."

run-server-remote:
	@echo "Starting server on remote..."
	@ssh $(REMOTE_USER)@$(REMOTE_HOST) \
		"cd $(REMOTE_PATH)/pi-weather; nohup venv/bin/python3 pi_weather/app/app.py  >/dev/null 2>/dev/null </dev/null  &"
	@echo "Server started on remote."

	@echo "Adding cronjob to start server on boot..."
	@ssh $(REMOTE_USER)@$(REMOTE_HOST) \
		"(crontab -l 2>/dev/null; echo '@reboot cd $(REMOTE_PATH)/pi-weather && venv/bin/python3 pi_weather/app/app.py') | crontab -"
	@echo "Cronjob added."

stop-server-remote:
	@ssh $(REMOTE_USER)@$(REMOTE_HOST) \
		"pkill -f 'python3 pi_weather/app/app.py'"
	@echo "Server stopped on remote."

remove-server-remote: stop-server-remote
	@echo "Removing server from remote..."
	@ssh $(REMOTE_USER)@$(REMOTE_HOST) \
		"rm -rf $(REMOTE_PATH)/pi-weather"
	@echo "Server removed from remote."

	@echo "Removing cronjob to start server on boot..."
	@ssh $(REMOTE_USER)@$(REMOTE_HOST) \
		"crontab -l | grep -v 'pi_weather/app' | crontab -"
	@echo "Cronjob removed."

update-server-remote: remove-server-remote deploy setup-server-remote run-server-remote
	@echo "Server updated on remote."


.PHONY: deploy-s2
deploy-s2:
	@echo "Deploying code tarball to remote sensor 2..."
	@scp code.tar.gz $(REMOTE_USER)@$(REMOTE_HOST_SENSOR_2):$(REMOTE_PATH)
	@echo "Code tarball copied to remote sensor."

	@echo "Deploying code on remote sensor 2..."
	@ssh $(REMOTE_USER)@$(REMOTE_HOST_SENSOR_2) \
		"mkdir -p $(REMOTE_PATH)/pi-weather; \
		tar -xzf $(REMOTE_PATH)/code.tar.gz -C $(REMOTE_PATH)/pi-weather && rm $(REMOTE_PATH)/code.tar.gz; \
		\
		cd $(REMOTE_PATH)/pi-weather; \
		python3 -m venv venv; source venv/bin/activate && pip install -r requirements-sensor.txt; \
		\
		crontab -l | { cat; echo \"*/5 * * * * cd $(REMOTE_PATH)/pi-weather && venv/bin/python3 pi_weather/sensor/sensor.py\"; } | crontab -"
	@echo "Code deployed to remote sensor successfully."

	@touch .last_deploy_sensor_2

clean-sensor-2:
	@echo "Removing cronjobs..."
	@ssh $(REMOTE_USER)@$(REMOTE_HOST_SENSOR_2) \
		"crontab -l | grep -v 'pi_weather/sensor' | crontab -"
	@echo "Cronjobs removed successfully."

	@echo "Removing code..."
	@ssh $(REMOTE_USER)@$(REMOTE_HOST_SENSOR_2) \
		"rm -rf $(REMOTE_PATH)/pi-weather"
	@echo "Code removed successfully."

deploy-sensor-2: clean-sensor-2 make-tar deploy-s2 remove-tar

update-sensor-2: clean-sensor-2 deploy-sensor-2
	@echo "Sensor 2 updated on remote."

remove-e-ink:
	@echo "Removing e-ink from remote..."
	@ssh $(REMOTE_USER)@$(REMOTE_HOST_E_INK) \
		"rm -rf $(REMOTE_PATH)/pi-weather/pi_weather/e_ink; \
		rm -rf $(REMOTE_PATH)/pi-weather/venv-ink; \
		rm ${REMOTE_PATH}/pi-weather/requirements-ink.txt; \
		crontab -l | grep -v 'pi_weather.e_ink' | crontab -;"
	@echo "E-ink removed from remote: code, venv and cronjob."

deploy-e-ink:
	@echo "Deploying code tarball to remote e-ink..."
	@scp code.tar.gz $(REMOTE_USER)@$(REMOTE_HOST_E_INK):$(REMOTE_PATH)
	@echo "Code tarball copied to remote e-ink host."

	@echo "Deploying code on remote e-ink..."
	@ssh $(REMOTE_USER)@$(REMOTE_HOST_E_INK) \
		"mkdir -p $(REMOTE_PATH)/pi-weather; \
		tar -xzf $(REMOTE_PATH)/code.tar.gz -C $(REMOTE_PATH)/pi-weather && rm $(REMOTE_PATH)/code.tar.gz; \
		\
		cd $(REMOTE_PATH)/pi-weather; \
		python3 -m venv venv-ink; source venv-ink/bin/activate && pip install -r requirements-ink.txt; \
		\
		cd $(REMOTE_PATH)/pi-weather && venv-ink/bin/python3 -m pi_weather.e_ink.display; \
		crontab -l | { cat; echo \"2-59/5 * * * * cd $(REMOTE_PATH)/pi-weather && venv-ink/bin/python -m pi_weather.e_ink.display\"; } | crontab -"
	@echo "Code deployed to remote e-ink successfully."

	@touch .last_deploy_e_ink

update-e-ink: make-tar remove-e-ink deploy-e-ink remove-tar
