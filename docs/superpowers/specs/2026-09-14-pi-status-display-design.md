# Pi/Home Status on the E-Ink Display — Design

## Context

`pi_weather/e_ink/display.py` currently draws sensor temperature readings
(from the `pi_weather` sqlite DB, via `db_utils.get_latest_sensor_data`) to
a Waveshare 2.13" V4 e-ink panel (`epd2in13_V4.EPD`), run as a one-shot
script on a cron schedule (`deploy-e-ink` Makefile target:
`2-59/5 * * * * ... python -m pi_weather.e_ink.display`).

The panel is attached to the same Raspberry Pi that also runs the `kass`
Telegram budget bot in Docker (`kass-budget-bot` container,
`restart: unless-stopped`, no `HEALTHCHECK` defined).

Goal: repurpose this panel to show Pi/home status — CPU temperature,
uptime, and Docker container status — replacing the weather screen
entirely.

## Non-goals

- Not showing weather and status together, or alternating between them.
- Not adding a `HEALTHCHECK` to `kass`'s Dockerfile in this change — Docker
  container status will reflect running/exited/restarting state, not
  application-level health, until/unless that's added separately.
- Not building a persistent daemon — stays a one-shot script on cron, like
  every other role in this project (server, sensor, e-ink).

## Architecture

New module `pi_weather/e_ink/status.py`, structured the same way as
`display.py`: a top-level script (no `if __name__` guard needed, matching
the existing convention) that gathers three independent pieces of data,
renders them into one image, and pushes that image to the panel.

```
status.py
  ├─ read_cpu_temp()      -> float | None
  ├─ read_uptime()        -> str | None
  ├─ read_docker_status() -> list[str] | None
  └─ main draw/display logic (mirrors display.py's EPD init/draw/sleep)
```

Each `read_*` function is independently callable and returns `None` (or an
empty result) on failure rather than raising, so a problem in one data
source does't prevent the other two from rendering. This is what makes the
per-line error handling below possible, and each function can be unit
tested without hardware or Docker access by mocking the one thing it reads
(a file path, or `subprocess.run`).

## Data collection

**CPU temperature** — read directly from
`/sys/class/thermal/thermal_zone0/temp` (millidegrees C, sysfs). No
`vcgencmd` dependency, no extra permissions required. On read failure
(file missing, permission denied, unparseable content), returns `None`.

**Uptime** — read `/proc/uptime` (first field, seconds as float), format as
a short human string, e.g. `3d 4h` or `47m` for under an hour. Same
failure handling as CPU temp.

**Docker container status** — shell out to
`docker ps -a --format '{{.Names}}: {{.Status}}'` via `subprocess.run`,
capturing stdout, with a short timeout (e.g. 5s) to avoid a hung Docker
daemon blocking the whole cron run. Returns one string per line (container
name + status, e.g. `kass-budget-bot: Up 2 hours`), or `None` if the
command fails (missing binary, permission denied, timeout, non-zero exit).

This reports Docker's own `Status` field (running / exited / restarting),
**not** application health — neither `kass`'s `Dockerfile` nor its
`docker-compose.yml` defines a `HEALTHCHECK`, so there is no richer signal
to read yet. Good enough to notice "the container isn't running"; not
enough to notice "it's running but broken." Listing is not scoped to a
specific container name, so it naturally picks up whatever's running on
the host without a hardcoded list.

## Rendering

Same pattern as `display.py`: monochrome PIL image
(`Image.new("1", (epd.height, epd.width), 255)`), `font20`
(`Font.ttc`, size 20), drawn top to bottom with a 25px line height,
rotated 180° before display (matching the panel's current mounting
orientation), then `epd.display(epd.getbuffer(image))` followed by
`epd.sleep()`.

Layout (x=5, y starts at 5, y_delta=25):

1. Timestamp — `current_date.strftime("%b %d, %H:%M")`
2. CPU temp — `f"CPU: {temp:.1f} C"`, or `"CPU: n/a"` if unavailable
3. Uptime — `f"Up: {uptime_str}"`, or `"Up: n/a"` if unavailable
4. One line per Docker container (name + status, truncated to fit the
   panel width if needed), or a single `"docker: n/a"` line if the
   `docker` call failed entirely, or `"docker: none running"` if it
   succeeded but returned zero containers.

With a 122×250px panel and 20px font at 25px line height, roughly 4-5
lines fit. This is fine for the current single-container setup; if the
number of containers grows enough to overflow the panel, that's a known
limitation to revisit later (e.g. truncate the list with a count), not
solved here (YAGNI for a homelab with one container).

## Error handling

- Each `read_*` function catches its own expected failure modes
  internally and returns `None`/empty rather than raising, so one bad
  source degrades to an "n/a" line instead of crashing the whole script
  and leaving the panel stuck on a stale image (mirrors the spirit of
  `display.py`'s early-exit-on-no-data, but per-section instead of
  all-or-nothing).
- The EPD init/display/sleep calls themselves are not wrapped in
  additional error handling beyond what `display.py` already does today —
  out of scope for this change.

## Deployment

- `deploy-e-ink` Makefile target and its crontab line switch from
  `-m pi_weather.e_ink.display` to `-m pi_weather.e_ink.status`. Same
  venv (`venv-ink`), same `requirements-ink.txt` (no new dependencies —
  `subprocess` and `os` are stdlib), same cadence
  (`2-59/5 * * * *`, i.e. every 5 minutes).
- `display.py` itself is left in place (not deleted) in case weather
  display is wanted again later or on a different panel; it's simply no
  longer what's cron'd on this device.

## Testing

- Unit tests for `read_cpu_temp`, `read_uptime`, and `read_docker_status`,
  each covering the success path and the "source unavailable" path
  (mocking the filesystem read / `subprocess.run` — no real hardware or
  Docker daemon needed), following the existing `pi_weather/app/test_app.py`
  pattern for how this repo structures tests.
- No test for the actual EPD drawing/display calls — `display.py` has none
  either, and doing so would need real (or heavily mocked) hardware, which
  isn't worth it for a one-shot cron script whose drawing logic is a
  direct visual check (look at the panel after a deploy).
