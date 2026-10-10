# Shimano BT-E6000 / BT-E6010 UART field logs (October 2026)

Independent repair-lab observations shared for protocol research. The battery status byte `0x25` is an observation, **not** a confirmed diagnosis or a proven permanent lock state. Data is provided as-is; no reverse-engineering claim about its root cause is made.

## Contents

- `RXTXRecords/Case_01`: BT-E6010, `0x25`. Original cell group 10 measured around 0.2 V. A temporary test cell restored readable S10 voltage and UART communication, but status remained `0x25` and the known startup sequence did not enable the output. This is a bench diagnostic configuration, not a repaired battery ready for use.
- `RXTXRecords/Case_02` (4 stages): BT-E6000, initially 24.61 V, status `0x00`; after controlled voltage recovery ~30.77 V, still `0x00`. An original charger was then connected; LEDs 1+5 flashed and the original fuse appeared open. Later charging measurements are included. Status remained `0x00`. These are service observations, not recommended repair procedures.
- `RXTXRecords/Case_03` and `Case_04`: separate healthy BT-E6010 serial exchanges, `0x00`.
- `RXTXRecords/Case_05`: BT-E6010 serial exchange reporting `0x25`; exact original battery identity not independently established.
- `RXTXRecords/Case_06`: BT-E6010 serial exchange reporting `0x25` (separate case).
- `RXTXRecords/Case_07`: long BT-E6010 discharge/polling trace; no assumption made about whether a cutoff is visible in the complete capture.

## Capture and tools

- Serial: 9600 baud, 8 data bits, no parity, 1 stop bit (8N1).
- `uart_lab_readonly_v4.py` is the lab's **active query tool**, not a passive bike-to-battery sniffer. It replays an existing startup exchange and polls commands `10 11 12 13 20 A0 A6 A7 AA AB BB CB`.
- The `TX`/`RX` logs from `write.py`-style captures use Python byte representations. Other logs use space-delimited hex and decoded voltage fields. They are different capture formats.
- The script requires `pyserial` (`pip install pyserial`) and the startup timing data file `startup_pickle` in the working directory. Set the serial `PORT` constant as appropriate. It appends to `uart_scan_v4.txt`.
- The file `startup_pickle` is a Python pickle from the existing lab workflow. **Do not unpickle data from untrusted sources**. The uploaded file was checked statically for pickle GLOBAL/REDUCE/BUILD-style execution opcodes; this does not establish a general safety guarantee. For protocol research, inspect it without executing it.
- The term `read-only` refers to the lab's intended non-configuration scan; the startup replay actively transmits bytes and the complete command semantics have not been formally verified. Do not connect untested commands to customer equipment without understanding the risks.

## Data hygiene and provenance

Original measurement bytes and timing were retained. Customer names were replaced with anonymous case IDs in filenames and in free-text headers. Identical duplicate uploads were omitted. The raw UART traffic may contain device-specific identifiers; review before making this repository public.

## Research questions

1. Which underlying condition causes status byte `0x25` in otherwise communicating BT-E6010 controllers?
2. Is the status latched independently of current cell voltage?
3. What do the observed transitions in the status/state fields signify, and what further non-destructive data could distinguish the failure modes?
