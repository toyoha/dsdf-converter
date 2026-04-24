import struct
import csv
import argparse
from collections import defaultdict
from datetime import datetime, timedelta, timezone

RECORD_SIZE = 96
HEADER_SKIP = 0x1000  # 必要に応じて調整

JST = timezone(timedelta(hours=9), name="JST")

def parse_record(chunk):
    sample_no = struct.unpack('<I', chunk[0:4])[0]
    date_raw = struct.unpack('<I', chunk[4:8])[0]
    time_ms = struct.unpack('<I', chunk[8:12])[0]

    # YYYYMMDD想定
    date_str = str(date_raw)
    try:
        base_dt = datetime.strptime(date_str, "%Y%m%d")
    except:
        return None

    # 元は "naive" として扱う
    dt = base_dt + timedelta(milliseconds=time_ms)

    # JSTとしてタイムゾーン付与（※ここ重要）
    dt_jst = dt.replace(tzinfo=JST)

    raw_vals = struct.unpack('<' + 'H'*20, chunk[16:56])

    return {
        "datetime_jst": dt_jst,
        "sample_no": sample_no,
        "raw": raw_vals
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("-o", "--out_prefix", default="output")
    args = parser.parse_args()

    with open(args.input, "rb") as f:
        data = f.read()

    grouped = defaultdict(list)

    for i in range(HEADER_SKIP, len(data), RECORD_SIZE):
        chunk = data[i:i+RECORD_SIZE]
        if len(chunk) < RECORD_SIZE:
            break

        rec = parse_record(chunk)
        if not rec:
            continue

        # 日付キーもtimezoneベース
        date_key = rec["datetime_jst"].astimezone(JST).strftime("%Y-%m-%d")
        grouped[date_key].append(rec)

    for date_key, records in grouped.items():
        filename = f"{args.out_prefix}_{date_key}.csv"

        with open(filename, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)

            header = ["datetime_iso8601", "sample_no"] + [f"raw_{i}" for i in range(20)]
            writer.writerow(header)

            for r in records:
                row = [
                    r["datetime_jst"].isoformat(timespec='milliseconds'),
                    r["sample_no"]
                ] + list(r["raw"])
                writer.writerow(row)

        print(f"出力: {filename}")

if __name__ == "__main__":
    main()