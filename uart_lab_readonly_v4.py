import serial
import time
import pickle
from datetime import datetime

PORT = "COM3"
BAUD = 9600

COMMANDS = [
    0x10, 0x11, 0x12, 0x13, 0x20,
    0xA0, 0xA6, 0xA7, 0xAA, 0xAB, 0xBB, 0xCB
]

BYTE_DELAY = 0.0025
RX_WAIT = 0.12
BETWEEN_CMDS = 0.08
LOG_FILE = "uart_scan_v4.txt"


def crc16_x25(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0x8408 if (crc & 1) else (crc >> 1)
    return crc ^ 0xFFFF


def build_cmd_frame(seq: int, cmd: int) -> bytes:
    body = bytes([seq & 0x03, 0x02, cmd & 0xFF, 0x00])
    crc = crc16_x25(body)
    return bytes([0x00]) + body + crc.to_bytes(2, "little")


def send_frame_slow(ser, frame: bytes) -> bytes:
    ser.reset_input_buffer()

    for b in frame:
        ser.write(bytes([b]))
        ser.flush()
        time.sleep(BYTE_DELAY)

    time.sleep(RX_WAIT)
    return ser.read_all()


def frame_hex(data: bytes) -> str:
    return data.hex(" ") if data else "<BRAK>"


def log_line(fp, text=""):
    print(text)
    fp.write(text + "\n")
    fp.flush()


def u16_le(data: bytes, offset: int):
    if offset < 0 or offset + 1 >= len(data):
        return None
    return data[offset] | (data[offset + 1] << 8)


def extract_frames(data: bytes):
    """
    Shimano frame observed here:
      00 | seq/header | LEN | CMD | payload... | CRC_lo | CRC_hi

    LEN appears to count CMD + payload bytes, so total frame length is:
      3 header bytes + LEN bytes + 2 CRC bytes = LEN + 5
    """
    frames = []
    i = 0

    while i + 5 <= len(data):
        if data[i] != 0x00:
            i += 1
            continue

        length = data[i + 2]
        total = length + 5

        if total < 6:
            i += 1
            continue

        if i + total <= len(data):
            frame = data[i:i + total]
            frames.append(frame)
            i += total
        else:
            break

    return frames


def decode_0x10(rx: bytes):
    if len(rx) < 10 or rx[0] != 0x00 or rx[3] != 0x10:
        return None

    length = rx[2]
    expected = length + 5
    if len(rx) < expected:
        return None

    # CMD is rx[3], payload starts at rx[4], CRC occupies last 2 bytes
    p = rx[4:expected - 2]

    # Known sample payload:
    # 25 01 00 00 00 BE 95 F8 1D EC 1D 14 13 14 4A 00 00 00 00 00 00
    if len(p) < 15:
        return None

    status = p[0]
    state = p[1]

    pack_raw = u16_le(p, 5)
    vmax_raw = u16_le(p, 7)
    vmin_raw = u16_le(p, 9)

    t1 = p[11]
    t2 = p[12]
    t3 = p[13]
    soc = p[14]

    return {
        "status": status,
        "state": state,
        "pack_v": pack_raw / 1000.0 if pack_raw is not None else None,
        "vmax_v": vmax_raw / 2000.0 if vmax_raw is not None else None,
        "vmin_v": vmin_raw / 2000.0 if vmin_raw is not None else None,
        "temps": [t1, t2, t3],
        "soc": soc,
    }


def decode_0xA0(rx: bytes):
    if len(rx) < 10 or rx[0] != 0x00 or rx[3] != 0xA0:
        return None

    length = rx[2]
    expected = length + 5
    if len(rx) < expected:
        return None

    p = rx[4:expected - 2]

    # Observed A0 payload:
    # first 4 bytes unknown/reserved,
    # then 10 x uint16 LE cell voltages in mV.
    if len(p) < 24:
        return None

    cells = []
    base = 4

    for i in range(10):
        raw = u16_le(p, base + i * 2)
        if raw is None:
            return None
        cells.append(raw / 1000.0)

    return {
        "cells": cells,
        "min_v": min(cells),
        "max_v": max(cells),
        "avg_v": sum(cells) / len(cells),
        "sum_v": sum(cells),
        "delta_mv": (max(cells) - min(cells)) * 1000.0,
    }


def print_decode_0x10(fp, d):
    log_line(fp, "DECODE 0x10:")
    log_line(fp, f"  STATUS:   0x{d['status']:02X}")
    log_line(fp, f"  STATE:    0x{d['state']:02X}")

    if d["pack_v"] is not None:
        log_line(fp, f"  PACK:     {d['pack_v']:.3f} V")

    log_line(fp, f"  SOC:      {d['soc']} %")
    log_line(fp, "  TEMP:     " + " / ".join(f"{x} C" for x in d["temps"]))

    if d["vmin_v"] is not None:
        log_line(fp, f"  CELL MIN: {d['vmin_v']:.3f} V")

    if d["vmax_v"] is not None:
        log_line(fp, f"  CELL MAX: {d['vmax_v']:.3f} V")

    if d["vmin_v"] is not None and d["vmax_v"] is not None:
        delta = (d["vmax_v"] - d["vmin_v"]) * 1000.0
        log_line(fp, f"  DELTA:    {delta:.0f} mV")


def print_decode_0xA0(fp, d):
    log_line(fp, "DECODE 0xA0:")

    for i, v in enumerate(d["cells"], start=1):
        log_line(fp, f"  S{i:02d}: {v:.3f} V")

    log_line(fp, f"  MIN:   {d['min_v']:.3f} V")
    log_line(fp, f"  MAX:   {d['max_v']:.3f} V")
    log_line(fp, f"  AVG:   {d['avg_v']:.3f} V")
    log_line(fp, f"  SUM:   {d['sum_v']:.3f} V")
    log_line(fp, f"  DELTA: {d['delta_mv']:.0f} mV")


def decode_frame(fp, frame: bytes):
    if len(frame) < 6:
        return

    cmd = frame[3]

    if cmd == 0x10:
        d = decode_0x10(frame)
        if d:
            print_decode_0x10(fp, d)

    elif cmd == 0xA0:
        d = decode_0xA0(frame)
        if d:
            print_decode_0xA0(fp, d)


def decode_rx_buffer(fp, data: bytes):
    frames = extract_frames(data)

    for frame in frames:
        decode_frame(fp, frame)


def replay_startup(ser, fp):
    with open("startup_pickle", "rb") as f:
        startup = pickle.load(f)

    log_line(fp, "Startup jak w oryginalnym write.py...")

    start = time.time()
    base_time = startup[0][0]["time"]

    for i, batch in enumerate(startup):
        for rec in batch:
            target = rec["time"] - base_time

            while time.time() - start < target:
                time.sleep(0.0005)

            ser.write(rec["byte"])
            ser.flush()

        time.sleep(0.08)
        rx = ser.read_all()

        log_line(fp, f"{i:03d} RX: {frame_hex(rx)}")

        if rx:
            decode_rx_buffer(fp, rx)

    log_line(fp, "")
    log_line(fp, "Startup done.")
    log_line(fp, "")


def scan_commands(ser, fp):
    seq = 0

    log_line(fp, "AUTOMATYCZNY READ-ONLY SCAN")
    log_line(fp, "Komendy: " + " ".join(f"{c:02X}" for c in COMMANDS))
    log_line(fp, "")

    for cmd in COMMANDS:
        frame = build_cmd_frame(seq, cmd)

        log_line(fp, f"CMD {cmd:02X} / SEQ {seq}")
        log_line(fp, "TX: " + frame.hex(" "))

        rx = send_frame_slow(ser, frame)

        log_line(fp, "RX: " + frame_hex(rx))

        if rx:
            decode_rx_buffer(fp, rx)

        log_line(fp, "")

        seq = (seq + 1) & 0x03
        time.sleep(BETWEEN_CMDS)

    return seq


def interactive_mode(ser, fp, start_seq=0):
    seq = start_seq & 0x03

    log_line(fp, "TRYB RĘCZNY")
    log_line(fp, "Dozwolone: " + " ".join(f"{c:02X}" for c in COMMANDS))
    log_line(fp, "q = koniec")
    log_line(fp, "")

    while True:
        raw = input("CMD hex > ").strip()

        if raw.lower() in {"q", "quit", "exit"}:
            break

        try:
            cmd = int(raw, 16)
        except ValueError:
            print("Błąd: wpisz np. 11 albo A0.")
            continue

        if cmd not in COMMANDS:
            print("Ta komenda nie jest na liście read-only.")
            continue

        frame = build_cmd_frame(seq, cmd)

        log_line(fp, f"CMD {cmd:02X} / SEQ {seq}")
        log_line(fp, "TX: " + frame.hex(" "))

        rx = send_frame_slow(ser, frame)

        log_line(fp, "RX: " + frame_hex(rx))

        if rx:
            decode_rx_buffer(fp, rx)

        log_line(fp, "")
        seq = (seq + 1) & 0x03


def main():
    ser = serial.Serial(
        PORT,
        baudrate=BAUD,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=0
    )

    with open(LOG_FILE, "a", encoding="utf-8") as fp:
        log_line(fp, "=" * 72)
        log_line(fp, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        log_line(fp, f"{PORT} / {BAUD} 8N1")
        log_line(fp, f"BYTE_DELAY={BYTE_DELAY}s  RX_WAIT={RX_WAIT}s")
        log_line(fp, "=" * 72)
        log_line(fp, "")

        try:
            replay_startup(ser, fp)
            next_seq = scan_commands(ser, fp)
            interactive_mode(ser, fp, start_seq=next_seq)

        except KeyboardInterrupt:
            log_line(fp, "")
            log_line(fp, "Przerwano Ctrl+C.")

        finally:
            ser.close()


if __name__ == "__main__":
    main()
