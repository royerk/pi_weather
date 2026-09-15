# Pi/Home Status E-Ink Display Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers-extended-cc:subagent-driven-development (if subagents available) or superpowers-extended-cc:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the e-ink panel's weather display with a Pi/home status screen (CPU temp, uptime, Docker container status), using partial refresh every 5 minutes and a full refresh once a day.

**Architecture:** Two new modules in `pi_weather/e_ink/`: `status_data.py` (pure stdlib data-gathering + refresh-decision functions, no PIL/EPD import, unit tested) and `status.py` (the cron entry point that imports PIL/EPD plus `status_data`'s functions and drives the panel — mirrors `display.py`'s existing structure, no automated test, verified visually on hardware). The `deploy-e-ink` Makefile target switches from `display` to `status`.

**Tech Stack:** Python 3, PIL (Pillow), the existing `epd2in13_V4` Waveshare driver, pytest, stdlib `subprocess`/file I/O.

**Spec:** `docs/superpowers/specs/2026-09-14-pi-status-display-design.md`

---

## Chunk 1: status_data.py, status.py, Makefile, and rollout

### Task 1: `status_data.py` — CPU temperature and uptime

**Files:**
- Create: `pi_weather/e_ink/status_data.py`
- Test: `pi_weather/e_ink/test_status_data.py`

- [ ] **Step 1: Write the failing tests**

Create `pi_weather/e_ink/test_status_data.py`:

```python
from pi_weather.e_ink.status_data import read_cpu_temp, read_uptime


def test_read_cpu_temp_parses_millidegrees(tmp_path):
    temp_file = tmp_path / "temp"
    temp_file.write_text("45123\n")

    assert read_cpu_temp(str(temp_file)) == 45.123


def test_read_cpu_temp_returns_none_when_file_missing(tmp_path):
    missing = tmp_path / "does_not_exist"

    assert read_cpu_temp(str(missing)) is None


def test_read_cpu_temp_returns_none_on_unparseable_content(tmp_path):
    temp_file = tmp_path / "temp"
    temp_file.write_text("not a number\n")

    assert read_cpu_temp(str(temp_file)) is None


def test_read_uptime_formats_days_and_hours(tmp_path):
    uptime_file = tmp_path / "uptime"
    # 3 days, 4 hours, 5 minutes = 3*86400 + 4*3600 + 5*60 = 273900
    uptime_file.write_text("273900.50 12345.67\n")

    assert read_uptime(str(uptime_file)) == "3d 4h"


def test_read_uptime_formats_hours_and_minutes_under_a_day(tmp_path):
    uptime_file = tmp_path / "uptime"
    # 2 hours, 30 minutes = 9000 seconds
    uptime_file.write_text("9000.0 100.0\n")

    assert read_uptime(str(uptime_file)) == "2h 30m"


def test_read_uptime_formats_minutes_under_an_hour(tmp_path):
    uptime_file = tmp_path / "uptime"
    uptime_file.write_text("47.0 10.0\n")

    assert read_uptime(str(uptime_file)) == "0m"


def test_read_uptime_returns_none_when_file_missing(tmp_path):
    missing = tmp_path / "does_not_exist"

    assert read_uptime(str(missing)) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd pi_weather-status && venv/bin/pytest pi_weather/e_ink/test_status_data.py -v`
(If `venv/` doesn't exist yet, run `make venv` first — see project `Makefile`.)
Expected: FAIL — `ModuleNotFoundError: No module named 'pi_weather.e_ink.status_data'`

- [ ] **Step 3: Write minimal implementation**

Create `pi_weather/e_ink/status_data.py`:

```python
"""Data-gathering helpers for the Pi/home status e-ink screen.

Deliberately has no PIL or EPD import (see
docs/superpowers/specs/2026-09-14-pi-status-display-design.md,
Architecture section) so this module can be imported and unit tested on
any machine, with or without e-ink hardware attached.
"""

import subprocess


def read_cpu_temp(path="/sys/class/thermal/thermal_zone0/temp"):
    try:
        with open(path) as f:
            raw = f.read().strip()
        return int(raw) / 1000.0
    except (OSError, ValueError):
        return None


def read_uptime(path="/proc/uptime"):
    try:
        with open(path) as f:
            raw = f.read().strip()
        seconds = float(raw.split()[0])
    except (OSError, ValueError, IndexError):
        return None

    days, remainder = divmod(int(seconds), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)

    if days > 0:
        return f"{days}d {hours}h"
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/bin/pytest pi_weather/e_ink/test_status_data.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add pi_weather/e_ink/status_data.py pi_weather/e_ink/test_status_data.py
git commit -m "Add CPU temp and uptime readers for e-ink status display"
```

---

### Task 2: `status_data.py` — Docker container status

**Files:**
- Modify: `pi_weather/e_ink/status_data.py`
- Modify: `pi_weather/e_ink/test_status_data.py`

- [ ] **Step 1: Write the failing tests**

Append to `pi_weather/e_ink/test_status_data.py` (add `from unittest.mock import patch` to the top-level imports, alongside the existing `from pi_weather.e_ink.status_data import ...` — extend that import line to include `read_docker_status`):

```python
def _fake_completed_process(stdout):
    return subprocess.CompletedProcess(
        args=["docker"], returncode=0, stdout=stdout, stderr=""
    )


@patch("pi_weather.e_ink.status_data.subprocess.run")
def test_read_docker_status_parses_container_lines(mock_run):
    mock_run.return_value = _fake_completed_process(
        "kass-budget-bot: Up 2 hours\n"
    )

    assert read_docker_status() == ["kass-budget-bot: Up 2 hours"]


@patch("pi_weather.e_ink.status_data.subprocess.run")
def test_read_docker_status_returns_empty_list_when_no_containers(mock_run):
    mock_run.return_value = _fake_completed_process("")

    assert read_docker_status() == []


@patch("pi_weather.e_ink.status_data.subprocess.run")
def test_read_docker_status_returns_none_when_docker_missing(mock_run):
    mock_run.side_effect = FileNotFoundError()

    assert read_docker_status() is None


@patch("pi_weather.e_ink.status_data.subprocess.run")
def test_read_docker_status_returns_none_on_timeout(mock_run):
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="docker", timeout=5)

    assert read_docker_status() is None


@patch("pi_weather.e_ink.status_data.subprocess.run")
def test_read_docker_status_returns_none_on_nonzero_exit(mock_run):
    mock_run.side_effect = subprocess.CalledProcessError(
        returncode=1, cmd="docker"
    )

    assert read_docker_status() is None
```

This also requires adding `import subprocess` to the top of the test file (needed for `subprocess.CompletedProcess`/`TimeoutExpired`/`CalledProcessError`), and updating the existing import line to:

```python
from pi_weather.e_ink.status_data import read_cpu_temp, read_docker_status, read_uptime
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/bin/pytest pi_weather/e_ink/test_status_data.py -v`
Expected: the 5 new tests FAIL with `ImportError: cannot import name 'read_docker_status'`

- [ ] **Step 3: Write minimal implementation**

Add to `pi_weather/e_ink/status_data.py` (after `read_uptime`):

```python
def read_docker_status():
    try:
        result = subprocess.run(
            ["docker", "ps", "-a", "--format", "{{.Names}}: {{.Status}}"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
    except (subprocess.SubprocessError, OSError):
        return None

    return [line for line in result.stdout.splitlines() if line.strip()]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/bin/pytest pi_weather/e_ink/test_status_data.py -v`
Expected: 12 passed

- [ ] **Step 5: Commit**

```bash
git add pi_weather/e_ink/status_data.py pi_weather/e_ink/test_status_data.py
git commit -m "Add Docker container status reader for e-ink status display"
```

---

### Task 3: `status_data.py` — full/partial refresh decision

**Files:**
- Modify: `pi_weather/e_ink/status_data.py`
- Modify: `pi_weather/e_ink/test_status_data.py`

- [ ] **Step 1: Write the failing tests**

Append to `pi_weather/e_ink/test_status_data.py` (extend the import line again to include `record_full_refresh, should_do_full_refresh`, and add `from datetime import datetime` to the imports):

```python
def test_should_do_full_refresh_when_state_file_missing(tmp_path):
    state_file = tmp_path / "last_full_refresh"
    now = datetime(2026, 9, 15, 0, 2)

    assert should_do_full_refresh(str(state_file), now) is True


def test_should_do_full_refresh_when_state_file_empty(tmp_path):
    state_file = tmp_path / "last_full_refresh"
    state_file.write_text("")
    now = datetime(2026, 9, 15, 0, 2)

    assert should_do_full_refresh(str(state_file), now) is True


def test_should_not_do_full_refresh_when_already_done_today(tmp_path):
    state_file = tmp_path / "last_full_refresh"
    state_file.write_text("2026-09-15")
    now = datetime(2026, 9, 15, 12, 30)

    assert should_do_full_refresh(str(state_file), now) is False


def test_should_do_full_refresh_when_state_file_has_different_date(tmp_path):
    state_file = tmp_path / "last_full_refresh"
    state_file.write_text("2026-09-14")
    now = datetime(2026, 9, 15, 0, 2)

    assert should_do_full_refresh(str(state_file), now) is True


def test_record_full_refresh_writes_todays_date(tmp_path):
    state_file = tmp_path / "last_full_refresh"
    now = datetime(2026, 9, 15, 0, 2)

    record_full_refresh(str(state_file), now)

    assert state_file.read_text() == "2026-09-15"


def test_record_full_refresh_overwrites_existing_content(tmp_path):
    state_file = tmp_path / "last_full_refresh"
    state_file.write_text("2026-09-14")
    now = datetime(2026, 9, 15, 0, 2)

    record_full_refresh(str(state_file), now)

    assert state_file.read_text() == "2026-09-15"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/bin/pytest pi_weather/e_ink/test_status_data.py -v`
Expected: the 6 new tests FAIL with `ImportError: cannot import name 'should_do_full_refresh'`

- [ ] **Step 3: Write minimal implementation**

Add to `pi_weather/e_ink/status_data.py` (after `read_docker_status`):

```python
def should_do_full_refresh(state_file, now):
    try:
        with open(state_file) as f:
            last = f.read().strip()
    except OSError:
        return True
    return last != now.date().isoformat()


def record_full_refresh(state_file, now):
    try:
        with open(state_file, "w") as f:
            f.write(now.date().isoformat())
    except OSError:
        pass
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/bin/pytest pi_weather/e_ink/test_status_data.py -v`
Expected: 18 passed

- [ ] **Step 5: Commit**

```bash
git add pi_weather/e_ink/status_data.py pi_weather/e_ink/test_status_data.py
git commit -m "Add full/partial refresh state tracking for e-ink status display"
```

---

### Task 4: `status.py` — the cron entry point that draws the panel

**Files:**
- Create: `pi_weather/e_ink/status.py`

No automated test for this file (matches `display.py`'s existing precedent and the spec's Testing section) — importing it requires the EPD driver, which only loads on real hardware. Verification is a visual check on the physical panel in Task 7.

- [ ] **Step 1: Write `status.py`**

Create `pi_weather/e_ink/status.py`:

```python
import os
import time
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

from pi_weather.e_ink.epd2in13_V4 import EPD
from pi_weather.e_ink.status_data import (
    read_cpu_temp,
    read_docker_status,
    read_uptime,
    record_full_refresh,
    should_do_full_refresh,
)

STATE_FILE = "/tmp/pi_weather_eink_last_full_refresh"
DOCKER_LINE_MAX_CHARS = 30

font20 = ImageFont.truetype(os.path.join(os.path.dirname(__file__), "Font.ttc"), 20)

now = datetime.now()
full_refresh = should_do_full_refresh(STATE_FILE, now)

epd = EPD()
epd.init()
if full_refresh:
    epd.Clear(0xFF)

image = Image.new("1", (epd.height, epd.width), 255)
draw = ImageDraw.Draw(image)
x = 5
y = 5
y_delta = 25

draw.text((x, y), now.strftime("%b %d, %H:%M"), font=font20, fill=0)
y += y_delta

cpu_temp = read_cpu_temp()
cpu_line = f"CPU: {cpu_temp:.1f} C" if cpu_temp is not None else "CPU: n/a"
draw.text((x, y), cpu_line, font=font20, fill=0)
y += y_delta

uptime = read_uptime()
uptime_line = f"Up: {uptime}" if uptime is not None else "Up: n/a"
draw.text((x, y), uptime_line, font=font20, fill=0)
y += y_delta

containers = read_docker_status()
if containers is None:
    docker_lines = ["docker: n/a"]
elif len(containers) == 0:
    docker_lines = ["docker: none running"]
else:
    docker_lines = [line[:DOCKER_LINE_MAX_CHARS] for line in containers]

for i, line in enumerate(docker_lines):
    draw.text((x, y + i * y_delta), line, font=font20, fill=0)

image = image.rotate(180)

if full_refresh:
    epd.displayPartBaseImage(epd.getbuffer(image))
    record_full_refresh(STATE_FILE, now)
else:
    epd.displayPartial(epd.getbuffer(image))

epd.sleep()
```

- [ ] **Step 2: Sanity-check the file parses (no hardware needed for this check)**

Run: `venv/bin/python -c "import ast; ast.parse(open('pi_weather/e_ink/status.py').read())"`
Expected: no output (silent success — this only checks the file is syntactically valid Python; it does not run it, since running it imports the EPD driver and requires hardware)

- [ ] **Step 3: Commit**

```bash
git add pi_weather/e_ink/status.py
git commit -m "Add status.py e-ink entry point: renders and displays Pi status"
```

---

### Task 5: Update `deploy-e-ink` Makefile target

**Files:**
- Modify: `Makefile:256-274` (the `deploy-e-ink` target)

- [ ] **Step 1: Update the two `display` references**

In `Makefile`, inside the `deploy-e-ink` target, change both occurrences of `pi_weather.e_ink.display` to `pi_weather.e_ink.status`:

```makefile
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
		cd $(REMOTE_PATH)/pi-weather && venv-ink/bin/python3 -m pi_weather.e_ink.status; \
		crontab -l | { cat; echo \"2-59/5 * * * * cd $(REMOTE_PATH)/pi-weather && venv-ink/bin/python -m pi_weather.e_ink.status\"; } | crontab -"
	@echo "Code deployed to remote e-ink successfully."

	@touch .last_deploy_e_ink
```

(Only the two `pi_weather.e_ink.display` → `pi_weather.e_ink.status` substitutions change; everything else in the target — `remove-e-ink`, `update-e-ink`, and the rest of the file — stays as-is. `remove-e-ink`'s `crontab -l | grep -v 'pi_weather.e_ink'` still matches either module name, since it greps on the package prefix, not the specific module — no change needed there.)

- [ ] **Step 2: Verify with a diff**

Run: `git diff Makefile`
Expected: exactly two changed lines, both `display` → `status`, no other changes

- [ ] **Step 3: Commit**

```bash
git add Makefile
git commit -m "Point deploy-e-ink at status.py instead of display.py"
```

---

### Task 6: Full verification pass (tests + lint)

**Files:** none (verification only)

- [ ] **Step 1: Run the full test suite**

Run: `venv/bin/pytest -v`
Expected: all tests pass, including the pre-existing `pi_weather/app/test_app.py` (which needs Docker running locally — if Docker isn't available in this environment, at minimum confirm `pi_weather/e_ink/test_status_data.py`'s 18 tests pass; note the `test_app.py` result either way)

- [ ] **Step 2: Run lint**

Run: `make lint`
Expected: `isort`, `black`, and `mdformat` all report clean or auto-fix formatting with no errors. If `black`/`isort` reformat `status_data.py`, `status.py`, or `test_status_data.py`, re-run Step 1 to confirm tests still pass after formatting.

- [ ] **Step 3: Commit any lint-driven formatting fixes**

```bash
git add -A
git status
```
If lint changed anything (check `git status` / `git diff --stat` first):
```bash
git commit -m "Apply lint formatting"
```
If lint changed nothing, skip this commit.

---

### Task 7: Deploy to the Pi and verify on real hardware

**Files:** none (deployment + manual verification)

This is the step where the spec's "Open risk, needs hardware validation" (cross-process partial refresh) gets checked for real — it cannot be verified any other way.

- [ ] **Step 1: Confirm deploy connectivity**

The `deploy-e-ink` Makefile target needs `REMOTE_USER`, `REMOTE_HOST_E_INK`, and `REMOTE_PATH` set (normally via a gitignored `.env` in the repo root, loaded by the Makefile's `-include .env`). Neither this worktree nor the main `pi_weather` checkout on this machine currently has a `.env` file, and there's no matching entry in `~/.ssh/config` for the e-ink host. Before running the deploy:
- If you have these values already (from how the existing weather deploy was set up), add a `.env` in the repo root with `REMOTE_USER=...`, `REMOTE_HOST_E_INK=...`, `REMOTE_PATH=...` (do not commit it — already covered by `.gitignore`'s `.env` entry).
- Confirm this machine can actually reach that host: `ssh $REMOTE_USER@$REMOTE_HOST_E_INK echo ok`.

- [ ] **Step 2: Merge the feature branch and deploy**

From the main `pi_weather` checkout (not this worktree, since `update-e-ink` reads `.env`/state from the repo root you run `make` in):

```bash
git fetch origin add-pi-status-display
git log --oneline origin/main..origin/add-pi-status-display
```
Review the commits, then merge (fast-forward, since this branch never diverged in a conflicting way):
```bash
git checkout main
git merge --ff-only origin/add-pi-status-display
make update-e-ink
```
Expected: `make update-e-ink`'s final output is `Code deployed to remote e-ink successfully.` with no error lines above it.

- [ ] **Step 3: Watch the panel over several cycles**

Wait for at least 3-4 cron cycles (roughly 15-20 minutes, given the `2-59/5 * * * *` schedule) and look at the panel:
- Confirm it now shows the timestamp/CPU/uptime/Docker status layout instead of weather.
- Confirm each partial-refresh update looks clean (text changes without visible ghosting/corruption building up). If ghosting or corruption appears after a few cycles, see the spec's fallback (drop the partial-refresh path, always full refresh) — that would be a follow-up change, not part of this plan.
- If possible, also observe one full-refresh cycle (the first run after local midnight, or force it by deleting `/tmp/pi_weather_eink_last_full_refresh` on the Pi via SSH and waiting for the next cron run) and confirm the screen does a full flash/clear rather than a silent partial update.

- [ ] **Step 4: Report back**

Summarize what the panel showed after the observation window (clean partial updates, or any ghosting/corruption observed) — this closes out the spec's open hardware-validation risk either way.
