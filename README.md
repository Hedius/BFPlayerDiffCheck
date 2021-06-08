# BF Player Diff Check & Unranked check
Simple tool for logging different player counts of battlefield servers. Writes data to stdout + to a csv.
Also used to log to discord if a server switches to
unranked while being online.

## Usage
```
usage: BFPlayerDiffCheck.py [-h] -v {bf3,bf4} -g GUID [-w CSV_FILE] [-i INTERVAL] [--webhook WEBHOOK]

Simple tool for logging different player counts of battlefield servers. Writes data to stdout + to a csv.

optional arguments:
  -h, --help            show this help message and exit
  -v {bf3,bf4}, --version {bf3,bf4}
                        Game version.
  -g GUID, --guid GUID  Server GUID
  -w CSV_FILE, --csv-file CSV_FILE
                        Optional path to csv log. Default server_log.csv
  -i INTERVAL, --interval INTERVAL
                        Logging interval in seconds. Min 10s.
  --webhook WEBHOOK     Discord webhook for unranked logging.
```


# Requirements
* aiohttp (`pip3 install --user -r requirements.txt` or use a venv)

# License
This project is free software and licensed under the GPLv3.
