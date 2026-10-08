# Ember Canal Control Handbook

Version: 8.3  
Coordinator: Zuri Mbeki  
Review date: 16 May 2048  
System identifier: `EC-GATE-903`

This handbook governs navigation, water allocation, maintenance, and incident response across the Ember Canal control network.

# Navigation Operations

## Lock schedule

The cargo barge *Solace* enters Lock Four at 06:25 every Tuesday and Thursday. Passage takes 38 minutes, and the required clearance token is `MARSH-27`.

## Opening checklist

1. Confirm that marker lamp Indigo is steady.
2. Set the east sluice to position 3.
3. Record the vessel draft with controller Mateo Lin.
4. Report a delayed passage on radio channel Reed-6.

# Water Allocation

The canal distributes 1,200 megalitres each week.

| District | Share | Weekly volume | Priority |
|---|---:|---:|---|
| Orchard | 45% | 540 ML | First |
| Foundry | 30% | 360 ML | Third |
| Wetland | 25% | 300 ML | Second |

## Conservation rules

- When reservoir storage falls below 420 ML, reduce Foundry delivery before changing Wetland delivery.
- When storage falls below 260 ML during nesting season, keep Wetland delivery at or above 300 ML and suspend Foundry delivery.
- Pump `KITE-11` may be restarted only by Zuri Mbeki or deputy coordinator Hana Rios.

# Maintenance Registry

| Component | Quantity | Location | Reorder rule |
|---|---:|---|---|
| Gate seals | 18 | Cabinet Delta | Reorder at 6 |
| Sensor floats | 11 | Rack South | Reorder at 4 |
| Signal relays | 7 | Drawer 12 | No automatic reorder |

## Calibration sequence

```text
OPEN PANEL M4
SELECT MODE QUIET-CURRENT
WAIT FOR FOUR GREEN PULSES
RECORD CHECKSUM EC83-FERN
```

If any pulse turns amber, stop the sequence and contact technician Priya Dane.

# Emergency Response

## Copper flood alert

When water rises above 5.8 metres, announce code **COPPER SWAN**, close Lock Four, and move canal crews to Shelter Juniper. Use channel Reed-6.

If a Copper alert begins while the *Solace* is inside Lock Four, open the west relief gate first, guide the barge to Mooring B, and then close Lock Four.

## Combined equipment failure

If pump `KITE-11` fails during a Copper alert, activate backup pump `MOSS-4`, repeat code **COPPER SWAN** every 15 minutes, and inspect the west relief gate before reopening navigation.

# Command Succession

If Zuri Mbeki is unavailable, Hana Rios assumes command. If both are unavailable, controller Mateo Lin coordinates evacuation but may not restart either pump.
