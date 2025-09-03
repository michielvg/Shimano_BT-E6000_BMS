# Shimano BT-E6000 BMS PCB

My old Shimano BT-E6000 battery gave up on me a couple of years back and I always wanted to check out what killed it. I did not get around to do that and seeing a custom IC on the back of the PCB I got to tracing the hole pcb to try and figure out how it all ticks.

Right now I traced most of it, and the KiCAD project contains a messy schematic file. I hope to continue my work on it, but I wanted to put what I've done on here if I lose interest and perhaps to catch some of the mistakes I've made.

## Notes
### Possible Charging Initialization

TX Pin on charger provides 3.3V when connected to Battery RX pin.

1. RX at 3.3V to GND
2. Q024 (NPN) triggers
3. Q002 (PNP) triggers
4. Battery+ (BAT_P) or Pack+ (PACK_P) via common cathode diode (D004) provide 36v to LDO (IC002)
5. LDO powers MCU (IC003)
6. MCU initializes, but before any communication PIN19 has to go high to take over triggering Q024.

IC003 is not constantly powered.

###IC003

| PIN | DIRECTION | NOTE |
|--|--|--|
| 01 | OUT | Enable led D009
| 02 | OUT | Enable led D008
| 03 | IN (ADC)| Connected to IC001 VOUT, monitors Cell or Pack voltage. 
| 04 | IN (ADC)| Thermistor TH002 - SMD next to MOSFETS
| 05 | IN (ADC)| Thermistor TH003 - Between batteries
| 06 | IN (ADC)| Thermistor TH004 - TH
| 07 | ? | Capacitor to GND
| 08 | ? | Capacitor to GND
| 09 | ? | Capacitor to GND
| 10 | POWER | GND
| 11 |  | NC
| 12 | OUT | Enable Charging
| 13 | OUT | Enable Discharging
| 14 | IN | Connected to IC001 XALERT, L == ALERT
| 15 | ? | Unclear
| 16 | OUT | Enable PACK_P to IC001 PACK pin.
| 17 |  | NC
| 18 | OUT | Enable BAT_P to IC001 PACK pin
| 19 | OUT | Enables BAT_P or PACK_P to LDO (IC002)
| 20 |  | NC
| 21 | OUT | Enable IC001 EEPROM writing
| 22 | OUT | Puts 3.3V on TX of pack (?)
| 23 | IN | Flag to check if TX is high. Possibly used to verify pin 22 or to check if TX is beeing pulled low externally. (?)
| 24 | OUT | Enable led D012
| 25 | POWER | GND
| 26 | POWER | 3.3V
| 27 |  | RX-TX things still to figure out/review
| 28 |  | RX-TX things still to figure out/review
| 29 |  | TP - Unclear
| 30 |  | NC (?)
| 31 |  | RX-TX things still to figure out/review
| 32 |  | RX-TX things still to figure out/review
| 33 | IN | ON/OFF Button
| 34 | OUT | I2C Clock
| 35 | IO | I2C Data
| 36 |  | TP - Unclear
| 37 |  | Enable led D011
| 38 |  | NC
| 39 |  | NC
| 40 |  | NC
| 41 |  | NC
| 42 |  | NC
| 43 |  | NC
| 44 |  | NC
| 45 |  | NC
| 46 |  | NC
| 47 |  | NC
| 48 |  | Enable led D010