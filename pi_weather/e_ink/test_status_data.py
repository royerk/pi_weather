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
