# Ember Canal Lock Operations Guide

## Overview

The Ember Canal runs 31 km from Calder Basin to the Ember estuary through nine locks. This guide is
for lock keepers on duty at Lock 5 (Heron Lock), the deepest lock on the canal.

## Lock dimensions

| Lock | Length (m) | Width (m) | Rise (m) |
|------|-----------:|----------:|---------:|
| Lock 4 | 22.0 | 4.3 | 2.1 |
| Lock 5 (Heron) | 26.5 | 4.6 | 3.8 |
| Lock 6 | 22.0 | 4.3 | 1.9 |

## Opening hours

Locks are operated from 08:00 to 19:00 between April and October, and from 09:00 to 16:00 in winter.

## Water conservation rules

When the canal authority declares a conservation order, lock keepers limit Heron Lock to 12 cycles
a day, use the side pond for every cycle, and only work the lock for leisure boats in groups of at
least three.

## Towpath maintenance

The towpath is mown every three weeks in summer. Report fallen trees to the maintenance depot.

## Visitor moorings

Visitor moorings above Heron Lock are limited to 48 hours. Boats must not moor on the lock landing.

## Back-pump failure

If the Heron back-pump fails, close the upper paddles, start the standby pump within 20 minutes,
and record the fault code from the pump panel in the lock log.

## Ice and frost

Do not operate the lock when ice is more than 2 cm thick on the pound above.

## Fees and licences

Every boat needs a current canal licence. Short-term visitor licences cost 15 pounds per day.

## Alert levels

An amber alert means a pound is falling faster than 10 cm an hour: stop all leisure lockings and
phone the duty engineer. A red alert means a breach is suspected: close every gate and paddle.

## Barge in the chamber during an alert

If a barge is inside the lock chamber when an alert is raised, keep both gates closed, hold the
chamber level steady, and secure the barge with two lines fore and two lines aft.

## Telemetry configuration

```
station = heron-lock-5
report_interval_s = 300
level_alarm_cm_per_h = 10
```

## Training

New lock keepers shadow an experienced keeper for ten shifts before working alone.
