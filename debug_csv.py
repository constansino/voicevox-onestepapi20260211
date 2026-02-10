import csv

with open('/root/voicevox_trilingual.csv', 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    header = next(reader)
    print(f"Header: {header}")
    print(f"Header type: {[type(h) for h in header]}")
    print(f"Header repr: {[repr(h) for h in header]}")
