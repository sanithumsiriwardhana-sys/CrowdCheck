# Field logging guide

Stand at a stop (e.g. Malabe / SLIIT junction) during 7-9am or 5-7pm and log every bus on routes 177, 170, 190 and 17.
Add one row per bus to `field_logs.csv`:

| column | example | meaning |
|---|---|---|
| date | 2026-10-05 | YYYY-MM-DD |
| time | 07:40 | time the bus arrived (24h) |
| route | 177 | 177, 170, 190 or 17 |
| direction | to_kaduwela | where the bus is heading. 177: to_kaduwela / to_kollupitiya. 170: to_athurugiriya / to_pettah. 190: to_meegoda / to_pettah. 17: to_kandy / to_panadura |
| crowd_level | 0-3 | 0 seats free, 1 standing room, 2 packed, 3 can't board |
| rain_mm | 0 | 0 if dry; rough guess if raining (2 light, 8 heavy) |
| notes | skipped stop | optional |

Then retrain: `python -m ml.train`. Field log rows count 5x more than synthetic rows.
