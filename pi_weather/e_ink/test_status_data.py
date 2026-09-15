import subprocess
from datetime import datetime
from unittest.mock import patch

from pi_weather.e_ink.status_data import (
    read_cpu_temp,
    read_docker_status,
    read_uptime,
    record_full_refresh,
    should_do_full_refresh,
)


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


def _fake_completed_process(stdout):
    return subprocess.CompletedProcess(
        args=["docker"], returncode=0, stdout=stdout, stderr=""
    )


@patch("pi_weather.e_ink.status_data.subprocess.run")
def test_read_docker_status_parses_container_lines(mock_run):
    mock_run.return_value = _fake_completed_process("kass-budget-bot: Up 2 hours\n")

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
    mock_run.side_effect = subprocess.CalledProcessError(returncode=1, cmd="docker")

    assert read_docker_status() is None


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
