"""
PVC Swim Stats — CSV to JSON Converter
---------------------------------------
Usage:
    python convert_swim.py

Edit INPUT_FILE and OUTPUT_FILE below to match your setup.
Run this whenever you have fresh data from Access/Excel.
The output JSON is ready to paste into pvc_swim_stats.html.
"""

import csv, json, os
from datetime import datetime

# ── CONFIGURE THESE ───────────────────────────────────────────────────────────
INPUT_FILE  = "ResultsPVC.txt"   # Your exported CSV/TXT from Access or Excel
OUTPUT_FILE = "swim_data.json"   # Output JSON file
# ─────────────────────────────────────────────────────────────────────────────

AGE_GROUP_FIXES = {
    "10-Sep": "9-10",
    "12-Nov": "11-12",
    "8-Jul":  "7-8",
}

def normalize_name(name):
    """Strip middle initials and fix capitalization: 'smith, john A' → 'Smith, John'"""
    if not name or ',' not in name:
        return name
    last, rest = name.split(',', 1)
    first_parts = rest.strip().split()
    first = first_parts[0].capitalize() if first_parts else ''
    return f"{last.strip().title()}, {first}"

def parse_date(s):
    for fmt in ('%m/%d/%Y %H:%M:%S', '%m/%d/%Y', '%Y-%m-%d'):
        try:
            dt = datetime.strptime(s.strip(), fmt)
            return dt.strftime('%Y-%m-%d'), dt.year
        except ValueError:
            continue
    return s.strip(), ''

def to_float(v):
    try:    return float(v.strip())
    except: return None

def convert(input_file, output_file):
    if not os.path.exists(input_file):
        print(f"ERROR: Cannot find '{input_file}'")
        print("Make sure the script is in the same folder as your CSV, or update INPUT_FILE.")
        return

    records = []
    with open(input_file, encoding='latin-1') as f:
        reader = csv.DictReader(f)
        for row in reader:
            ag = AGE_GROUP_FIXES.get(row['Age Group'].strip(), row['Age Group'].strip())
            date_fmt, year = parse_date(row['Date'])
            swimmer = normalize_name(row['Swimmer Name'].strip())

            rec = {
                'id':            row['RowID'].strip(),
                'date':          date_fmt,
                'year':          year,
                'meet':          row['Meet Name'].strip(),
                'swimmer':       swimmer,
                'event_desc':    row['Event Description'].strip(),
                'event_type':    row['Event Type'].strip(),
                'gender':        row['Gender'].strip(),
                'age_group':     ag,
                'age':           row['Age'].strip(),
                'distance':      row['Distance (yd)'].strip(),
                'place':         row['Finished Place'].strip(),
                'total_swimmers':row['Total Swimmers'].strip(),
                'finals_display':row['Finals Time Display'].strip(),
                'finals_s':      to_float(row['Finals Time Total (s)']),
                'seed_display':  row['Seed Time Display'].strip(),
                'seed_s':        to_float(row['Seed Total Time (s)']),
                'pace_yd':       to_float(row['Time Per Yard']),
                'pace_m':        to_float(row['Time Per Meter']),
                'points':        row['Points'].strip(),
                'notation':      row['Result Notation'].strip(),
                'relay_team':    row['Relay Team'].strip(),
                'relay_pos1':    normalize_name(row['Relay Position 1'].strip()),
                'relay_pos2':    normalize_name(row['Relay Position 2'].strip()),
                'relay_pos3':    normalize_name(row['Relay Position 3'].strip()),
                'relay_pos4':    normalize_name(row['Relay Position 4'].strip()),
            }

            # Strip empty strings/None to keep JSON compact (but always keep swimmer)
            rec = {k: v for k, v in rec.items() if v != '' and v is not None}
            if 'swimmer' not in rec:
                rec['swimmer'] = swimmer
            records.append(rec)

    # Build meet options sorted chronologically
    meet_dates = {}
    for r in records:
        m, d = r.get('meet',''), r.get('date','')
        if m and d and (m not in meet_dates or d < meet_dates[m]):
            meet_dates[m] = d
    meet_options = []
    for meet, date in sorted(meet_dates.items(), key=lambda x: x[1]):
        dt = datetime.strptime(date, '%Y-%m-%d')
        meet_options.append({'value': meet, 'label': f"{dt.strftime('%b %d, %Y')} — {meet}"})

    # Write JSON
    data_str = json.dumps(records, separators=(',', ':'))
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(data_str)

    # Write meet options sidecar (optional, for reference)
    with open(output_file.replace('.json', '_meets.json'), 'w') as f:
        json.dump(meet_options, f, indent=2)

    size_kb = os.path.getsize(output_file) / 1024
    unique_swimmers = len(set(r.get('swimmer','') for r in records))

    print(f"\n✓ Done!")
    print(f"  {len(records):,} records  |  {unique_swimmers:,} unique swimmers  |  {len(meet_options)} meets")
    print(f"  Output: {output_file}  ({size_kb:.0f} KB)")
    print()
    print("Next steps — paste into pvc_swim_stats.html:")
    print("  1. Open swim_data.json in VS Code  →  Ctrl+A  →  Ctrl+C")
    print("  2. Open pvc_swim_stats.html in VS Code")
    print("  3. Ctrl+F  →  search:  const RAW_DATA=")
    print("  4. Select everything between the outer [  ] after RAW_DATA=")
    print("  5. Paste  →  Save  →  refresh browser")
    print()
    print("  For meet options (only needed if new meets were added):")
    print("  6. Open swim_data_meets.json  →  Ctrl+A  →  Ctrl+C")
    print("  7. In the HTML, find:  const MEET_OPTIONS=")
    print("  8. Replace the [  ] after it  →  Paste  →  Save")

if __name__ == '__main__':
    convert(INPUT_FILE, OUTPUT_FILE)