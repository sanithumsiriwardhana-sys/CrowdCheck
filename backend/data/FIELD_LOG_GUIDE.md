# Field logging guide (Route 177)

Stand at a stop (e.g. Malabe / SLIIT junction) during 7-9am or 5-7pm and log every Route 177 bus.
Add one row per bus to `field_logs.csv`:

| column | example | meaning |
|---|---|---|
| date | 2026-10-05 | YYYY-MM-DD |
| time | 07:40 | time the bus arrived (24h) |
| route | 177 | route number |
| direction | to_sliit / from_sliit | to_sliit = towards Kaduwela, from_sliit = towards Kollupitiya |
| crowd_level | 0-3 | 0 seats free, 1 standing room, 2 packed, 3 can't board |
| rain_mm | 0 | 0 if dry; rough guess if raining (2 light, 8 heavy) |
| notes | skipped stop | optional |

Then retrain: `python -m ml.train`. Field log rows count 5x more than synthetic rows.
