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

Two modules, split specifically so the data-gathering logic can be
imported and unit tested without pulling in PIL or the EPD driver:

```
status_data.py (new, stdlib only — no PIL/EPD import)
  ├─ read_cpu_temp()          -> float | None
  ├─ read_uptime()            -> str | None
  ├─ read_docker_status()     -> list[str] | None
  ├─ should_do_full_refresh(state_file, now) -> bool
  └─ record_full_refresh(state_file, now)    -> None

status.py (new, cron entry point — mirrors display.py's structure)
  imports the five functions above from status_data
  + PIL/EPD imports and draw/display logic at module scope,
    same top-level-script convention as display.py (no `if __name__` guard)
```

This split exists because `pi_weather/e_ink/epdconfig.py` does hardware
auto-detection at import time (instantiating a `RaspberryPi()` /
`JetsonNano()` driver unconditionally at module bottom) — merely
`import`ing `epd2in13_V4` (and therefore anything that imports it at
module scope, like `display.py` today) raises `RuntimeError: Cannot find sysfs_software_spi.so` on a machine without that hardware. Putting the
`read_*` functions in their own module with no PIL/EPD import means tests
can `from pi_weather.e_ink.status_data import read_cpu_temp, ...` on any
machine, hardware or not.

Each `read_*` function is independently callable and returns `None` (or an
empty result) on failure rather than raising, so a problem in one data
source doesn't prevent the other two from rendering. This is what makes
the per-line error handling below possible, and each function can be unit
tested by mocking the one thing it reads (a file path, or
`subprocess.run`) — no hardware, no Docker daemon, no new test
dependencies (see Testing).

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

## Refresh strategy: partial on every run, full once a day

The panel supports both a full refresh (`epd.display()` /
`epd.displayPartBaseImage()`, flashes the whole screen, slow, but resets
image quality) and a partial refresh (`epd.displayPartial()`, fast, no
flash, but accumulates ghosting over repeated use since it only diffs
against the previous image). Every 5-minute run does a partial refresh;
once a day, a run instead does a full refresh to clear accumulated
ghosting and re-establish a clean baseline.

Because `status.py` is a fresh process every cron run (no long-lived
daemon — see Non-goals), there's no in-memory way to know "have I done
today's full refresh yet." `should_do_full_refresh(state_file, now)` and
`record_full_refresh(state_file, now)` solve this with a one-line state
file (path e.g. `/tmp/pi_weather_eink_last_full_refresh`) holding the
ISO date of the last full refresh:

- `should_do_full_refresh` returns `True` if the file is missing, empty,
  unreadable, or its content doesn't equal `now.date().isoformat()`.
- `record_full_refresh` (only called after a successful full refresh)
  writes `now.date().isoformat()` to the file, overwriting it.

The existing cron schedule (`2-59/5 * * * *`) never fires exactly at
`00:00`, so this isn't a literal midnight check — in practice the first
run after midnight is the one at `00:02`, which is when the date rolls
over and triggers the full refresh. No crontab change needed; both paths
run from the same cron line, decided at runtime.

Using `/tmp` (tmpfs, cleared on reboot) is deliberate: it also forces a
full refresh on the first run after any reboot or redeploy, for free,
without a separate "is this a cold start" check — a fresh baseline is
exactly what you want after a restart anyway.

**Open risk, needs hardware validation:** partial refresh assumes the
panel's own internal "previous image" RAM survives between runs. Deep
sleep mode 1 (`epd.sleep()` already sends `0x10`/`0x01`, unchanged by
this spec) is documented to retain RAM, so this should hold — but
`display.py`, the only precedent in this codebase, only ever does full
refreshes, so there's no existing example here of partial refresh
surviving a process restart (`epd.init()`'s hardware reset, done fresh
every cron run). Verify by watching the panel over a few partial-refresh
cycles after deploying: if ghosting or corruption creeps in instead of
staying clean, the fallback is to drop the partial path and do a full
refresh every run (removing the state-file logic, not the daily-cadence
idea), or move off one-shot cron to a long-lived process — worth doing
only if the simple approach demonstrably fails.

## Rendering

Same pattern as `display.py`: monochrome PIL image
(`Image.new("1", (epd.height, epd.width), 255)`), `font20`
(`Font.ttc`, size 20), drawn top to bottom with a 25px line height,
rotated 180° before display (matching the panel's current mounting
orientation).

- **Full refresh path**: `epd.init()` → `epd.Clear(0xFF)` → draw →
  `epd.displayPartBaseImage(epd.getbuffer(image))` (seeds both the
  current *and* "previous" RAM banks the panel needs for clean partial
  diffing — not `epd.display()`, which only writes the current bank) →
  `record_full_refresh(...)` → `epd.sleep()`. Deliberately skips the
  `time.sleep(2)` that `display.py` does after `Clear()` — not an
  oversight; `TurnOnDisplay()` already blocks on `ReadBusy()`, so the
  extra sleep isn't needed for correctness.
- **Partial refresh path**: `epd.init()` → draw (no `Clear()` call) →
  `epd.displayPartial(epd.getbuffer(image))` → `epd.sleep()`.

A single `now = datetime.now()` is captured once per run and reused for
both the rendered timestamp line and the `should_do_full_refresh`/
`record_full_refresh` calls, rather than calling `datetime.now()`
separately for each — avoids (an admittedly unlikely, given the 5-minute
cadence) inconsistency if the two calls straddled a date boundary.

Layout is identical either way (x=5, y starts at 5, y_delta=25):

1. Timestamp — `current_date.strftime("%b %d, %H:%M")`
1. CPU temp — `f"CPU: {temp:.1f} C"`, or `"CPU: n/a"` if unavailable
1. Uptime — `f"Up: {uptime_str}"`, or `"Up: n/a"` if unavailable
1. One line per Docker container (name + status), each truncated to a
   fixed character count (e.g. 30 chars, `text[:30]`) rather than measured
   pixel width — simplest option, and precise pixel-fit isn't worth the
   complexity for a single-container homelab — or a single `"docker: n/a"`
   line if the `docker` call failed entirely, or `"docker: none running"`
   if it succeeded but returned zero containers.

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
- A failed *read* of the state file (missing, empty, unreadable) is
  treated as "do a full refresh" (see Refresh strategy) rather than an
  error — the safe default. A failed *write* after a full refresh is
  logged/ignored, not fatal — it just means tomorrow's run also does a
  full refresh, which is safe, only slightly wasteful.

## Deployment

- `deploy-e-ink` Makefile target references `-m pi_weather.e_ink.display`
  twice in its recipe — an initial one-shot smoke run right after the venv
  is created, and the crontab line itself — both need to change to
  `-m pi_weather.e_ink.status`. Same venv (`venv-ink`), same
  `requirements-ink.txt` (no new dependencies — `status_data.py` is
  stdlib-only, and `status.py` uses the PIL/EPD deps already listed
  there), same cadence (`2-59/5 * * * *`, i.e. every 5 minutes).
- `display.py` itself is left in place (not deleted) in case weather
  display is wanted again later or on a different panel; it's simply no
  longer what's cron'd on this device.

## Testing

- Unit tests for `status_data.read_cpu_temp`, `read_uptime`,
  `read_docker_status`, `should_do_full_refresh`, and
  `record_full_refresh`, each covering the success path and the "source
  unavailable"/edge-case path (mocking the filesystem read /
  `subprocess.run`; the refresh-decision functions can use a real temp
  file via `tmp_path` rather than mocking, since they're plain file I/O).
  Cases worth covering for `should_do_full_refresh`: missing file, empty
  file, file with today's date, file with a different date. Because
  `status_data.py` has no PIL/EPD import (see Architecture), these
  run under the project's existing `make test` / `requirements-dev.txt`
  venv exactly like `pi_weather/app/test_app.py` does today — no new test
  dependencies, no hardware, no Docker daemon required. Note this is a
  different testing *style* than `test_app.py` (which exercises the Flask
  app over HTTP against a real container) — it's a plain pytest module
  with `unittest.mock.patch`/`mock_open`, since there's no existing
  precedent in this repo for mocking a filesystem read or
  `subprocess.run`; this spec introduces that pattern rather than
  following one that already exists.
- No test for `status.py` itself (the PIL/EPD drawing and display calls) —
  same as `display.py`, which has none either — since that needs real (or
  heavily mocked) hardware, which isn't worth it for a one-shot cron
  script whose drawing logic is a direct visual check (look at the panel
  after a deploy).
