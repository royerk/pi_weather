PYTHON := python
APT_INSTALL := sudo apt install -y
SQLITE := sqlite3

clean:
	rm -rf venv
	echo "Virtual environment removed."

venv:
	@if [ -f venv ]; then \
        echo "Virtual environment exists"; \
    else \
        echo "Creating new virtual environment..."; \
        $(PYTHON) -m venv venv; \
        echo "Virtual environment created."; \
        echo "Activating new virtual environment..."; \
        . venv/bin/activate && pip -V; \
		$(PYTHON) -m pip install -r requirements-dev.txt; \
    fi

setup-server:
	$(APT_INSTALL) sqlite3
	$(PYTHON) -m pip install -r requirements-server.txt
	$(PYTHON) pi_weather/app/init_db.py

run-server:
	$(PYTHON) pi_weather/app/app.py

setup-sensor:
	$(PYTHON) -m pip install -r requirements-sensor.txt