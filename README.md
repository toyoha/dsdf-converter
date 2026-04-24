# dsdf-converter
`dsdf-converter` is a command-line utility for converting Defi Sports Display F (`.dsd`) telemetry logs into readable CSV files.

The tool parses binary DSDF log data, extracts timestamped telemetry records, and exports them in ISO8601 format with timezone support.

## Features

* Convert `.dsd` binary logs to CSV
* ISO8601 timestamps with timezone offset
* Split output files by local date
* Configurable timezone offset (`--tz`)
* Preserve raw telemetry channels for further analysis
* Designed for motorsport and vehicle telemetry workflows

## Output Format

Generated files are exported as:

```text
DSDF-YYYYMMDD.csv
```

Example:

```text
DSDF-20180803.csv
```

## Usage

```bash
python3 dsdf_converter.py input.dsd
```

Default timezone is JST (`+09:00`).

Specify a custom timezone offset:

```bash
python3 dsdf_converter.py input.dsd --tz 0
```

## Example Output

```text
datetime_iso8601,sample_no,raw_0,raw_1,...
2018-08-03T14:09:02.123+09:00,1234,...
```

## Notes

* The `.dsd` binary format is not publicly documented.
* This project uses reverse-engineering of actual DSDF log files.
* Raw channel mappings may vary depending on sensor configuration.

## Intended Use

This tool was created for analyzing telemetry data from tuned classic Mini vehicles using:

* Defi Sports Display F
* Weber carburetor setups
* 123TUNE+ ignition systems
* GPS and motorsport logging workflows
