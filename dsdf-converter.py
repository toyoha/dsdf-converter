import argparse
import csv
import struct
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


HEADER_SIZE = 112
RECORD_SIZE = 96
SIGNATURE = b"SportsDisplay-F\x00"
JST = timezone(timedelta(hours=9), name="JST")
OP_ADC_DIVISOR = 220.0

RAW_COLUMNS = [
    "UtcTime",
    "adTA",
    "adSP",
    "adTU",
    "adOP",
    "adFP",
    "adOT",
    "adWT",
    "adET",
    "obdTH",
    "obdIT",
    "adGear",
    "AccX",
    "AccY",
    "AccZ",
    "ROLL",
    "Pitch",
    "Yaw",
    "LAT",
    "LNG",
]

CSV_COLUMNS = [
    "datetime_iso8601",
    "Cnt",
    "SP_AD",
    "SP_AD_MPH",
    "adTA",
    "TU_AD",
    "OP_AD",
    "FP_AD",
    "DP_AD",
    "OT_AD",
    "WT_AD",
    "EGT_AD",
    "TH",
    "IN-Air",
    "adGear",
    "GX",
    "GY",
    "GZ",
    "RL",
    "PC",
    "YW",
    "LATITUDE",
    "LONGITUDE",
]


def be_u16(buf, offset):
    return struct.unpack_from(">H", buf, offset)[0]


def le_u16(buf, offset):
    return struct.unpack_from("<H", buf, offset)[0]


def le_i32(buf, offset):
    return struct.unpack_from("<i", buf, offset)[0]


def le_u32(buf, offset):
    return struct.unpack_from("<I", buf, offset)[0]


def find_default_xml(input_path):
    candidates = [
        Path.cwd() / "DefiSportsDisplayF.xml",
        input_path.parent / "DefiSportsDisplayF.xml",
        Path(__file__).resolve().parents[1] / "DefiSportsDisplayF.xml",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def load_xml_outputs(xml_path):
    if not xml_path:
        return []
    root = ET.parse(xml_path).getroot()
    outputs = []
    for elem in root.findall(".//OutputColumn"):
        name = (elem.text or "").strip()
        if name and name not in outputs:
            outputs.append(name)
    return outputs


def validate_output_columns(xml_outputs):
    ignored_intermediate = {
        "adTU_c",
        "AccX_c",
        "AccY_c",
        "AccZ_c",
        "ROOL_c",
        "ROLL_c",
        "Pitch_c",
        "Yaw_c",
        "HEADING",
    }
    emitted = set(CSV_COLUMNS)
    return [name for name in xml_outputs if name not in emitted and name not in ignored_intermediate]


def parse_record(chunk):
    year = struct.unpack_from("<H", chunk, 0)[0]
    month = chunk[2]
    day = chunk[3]
    utc_time = le_u32(chunk, 4)

    try:
        timestamp = datetime(year, month, day, tzinfo=JST) + timedelta(milliseconds=utc_time)
    except ValueError:
        return None

    raw = {
        "UtcTime": utc_time,
        "LAT": le_i32(chunk, 8),
        "LNG": le_i32(chunk, 12),
        "adTU": be_u16(chunk, 18),
        "AccX": be_u16(chunk, 20),
        "AccY": be_u16(chunk, 22),
        "AccZ": be_u16(chunk, 24),
        "ROLL": be_u16(chunk, 26),
        "Pitch": be_u16(chunk, 28),
        "Yaw": be_u16(chunk, 30),
        "adSP": le_u16(chunk, 40),
        "adTA": le_u16(chunk, 44),
        "adOP": le_u16(chunk, 48),
        "adFP": 0,
        "adOT": le_u16(chunk, 64),
        "adWT": le_u16(chunk, 68),
        "adET": le_u16(chunk, 72),
        "obdTH": 0,
        "obdIT": chunk[77],
        "adGear": chunk[78],
    }
    return {"datetime_jst": timestamp, "raw": raw, "calculated": calculate_values(raw)}


def calculate_values(raw):
    return {
        "Cnt": raw["UtcTime"] / 1000.0,
        "SP_AD": raw["adSP"] / 10.0,
        "SP_AD_MPH": raw["adSP"] / 16.093,
        "adTA": raw["adTA"],
        "TU_AD": (raw["adTU"] - 1000) / 10.0,
        "OP_AD": raw["adOP"] / OP_ADC_DIVISOR,
        "FP_AD": raw["adFP"] / 10.0,
        "DP_AD": raw["adFP"] - raw["adTU"],
        "OT_AD": raw["adOT"] / 20.0,
        "WT_AD": raw["adWT"] / 20.0,
        "EGT_AD": raw["adET"] / 5.0,
        "TH": raw["obdTH"] / 2.55,
        "IN-Air": raw["obdIT"],
        "adGear": raw["adGear"],
        "GX": (raw["AccX"] - 4000) / 1000.0,
        "GY": (raw["AccY"] - 4000) / 1000.0,
        "GZ": (raw["AccZ"] - 4000) / 1000.0,
        "RL": (raw["ROLL"] - 4000) / 1000.0,
        "PC": (raw["Pitch"] - 4000) / 1000.0,
        "YW": (raw["Yaw"] - 4000) / 1000.0,
        "LATITUDE": raw["LAT"] / 10000000.0,
        "LONGITUDE": raw["LNG"] / 10000000.0,
    }


def iter_records(data):
    if not data.startswith(SIGNATURE):
        raise ValueError("SportsDisplay-F signature was not found")

    usable_size = len(data) - HEADER_SIZE
    if usable_size < 0:
        return

    record_count = usable_size // RECORD_SIZE
    for index in range(record_count):
        start = HEADER_SIZE + index * RECORD_SIZE
        record = parse_record(data[start : start + RECORD_SIZE])
        if record:
            yield record


def format_value(name, value):
    if name == "datetime_iso8601":
        return value
    if name == "Cnt":
        return f"{value:.3f}"
    if name in {"SP_AD", "SP_AD_MPH", "TU_AD", "OP_AD", "FP_AD", "OT_AD", "WT_AD", "EGT_AD", "TH"}:
        return f"{value:.1f}"
    if name in {"GX", "GY", "GZ", "RL", "PC", "YW"}:
        return f"{value:.3f}"
    if name in {"LATITUDE", "LONGITUDE"}:
        return f"{value:.8f}"
    return value


def write_calculated_csv(path, records):
    with path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(CSV_COLUMNS)
        for record in records:
            calc = record["calculated"]
            row_values = {"datetime_iso8601": record["datetime_jst"].isoformat(timespec="milliseconds"), **calc}
            writer.writerow([format_value(name, row_values[name]) for name in CSV_COLUMNS])


def write_raw_csv(path, records):
    with path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["datetime_iso8601", *RAW_COLUMNS])
        for record in records:
            raw = record["raw"]
            writer.writerow([record["datetime_jst"].isoformat(timespec="milliseconds"), *[raw[name] for name in RAW_COLUMNS]])


def write_debug_csv(path, records):
    with path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["datetime_iso8601", *RAW_COLUMNS, *CSV_COLUMNS[1:]])
        for record in records:
            raw = record["raw"]
            calc = record["calculated"]
            row_values = {"datetime_iso8601": record["datetime_jst"].isoformat(timespec="milliseconds"), **calc}
            writer.writerow(
                [record["datetime_jst"].isoformat(timespec="milliseconds")]
                + [raw[name] for name in RAW_COLUMNS]
                + [format_value(name, row_values[name]) for name in CSV_COLUMNS[1:]]
            )


def main():
    parser = argparse.ArgumentParser(description="Convert Defi Sports Display F .dsd logs to CSV.")
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--out-prefix", default="output")
    parser.add_argument("--xml-profile", type=Path, help="DefiSportsDisplayF.xml path used to validate output columns")
    parser.add_argument("--raw", action="store_true", help="write raw decoded fields only")
    parser.add_argument("--debug", action="store_true", help="write raw decoded fields and calculated fields")
    args = parser.parse_args()

    input_path = args.input
    xml_path = args.xml_profile or find_default_xml(input_path)
    if xml_path:
        missing = validate_output_columns(load_xml_outputs(xml_path))
        if missing:
            print(f"Warning: XML output columns not emitted: {', '.join(missing)}")

    data = input_path.read_bytes()
    grouped = defaultdict(list)
    for record in iter_records(data):
        grouped[record["datetime_jst"].strftime("%Y-%m-%d")].append(record)

    for date_key, records in sorted(grouped.items()):
        suffix = "_raw" if args.raw else "_debug" if args.debug else ""
        output_path = Path(f"{args.out_prefix}_{date_key}{suffix}.csv")
        if args.raw:
            write_raw_csv(output_path, records)
            mode = "raw"
        elif args.debug:
            write_debug_csv(output_path, records)
            mode = "debug"
        else:
            write_calculated_csv(output_path, records)
            mode = "calculated"
        print(f"wrote {mode}: {output_path} ({len(records)} records)")


if __name__ == "__main__":
    main()
