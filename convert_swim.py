"""
PVC Swim Stats — CSV to JSON Converter + HTML Injector
Version: 2025-06-11 — includes event_num, event_code fields; (date, meet_name) deduplication
-------------------------------------------------------
Usage:
    python convert_swim.py /path/to/ResultsPVC.txt
    python convert_swim.py /path/to/ResultsPVC.txt --html /path/to/index.html
    python convert_swim.py /path/to/ResultsPVC.txt --html /path/to/index.html --out swim_data.json

Reads the input CSV/TXT, converts to JSON, and injects the data
directly into HTML_FILE — no copy/paste required.

Optionally also writes a standalone JSON file (--out) as a backup.
"""

import argparse, csv, json, os, re, shutil
from datetime import datetime

# ── CONFIGURE THESE DEFAULTS (overridden by command-line args) ────────────────
DEFAULT_HTML_FILE   = "index.html"       # The HTML file to inject data into
DEFAULT_OUTPUT_FILE = "swim_data.json"   # (Optional) standalone JSON backup
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

def convert(input_file, output_file, html_file):
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
                'event_num':     to_float(row['Event .'].strip()),
                'event_code':    row['Event Code'].strip(),
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

            rec = {k: v for k, v in rec.items() if v != '' and v is not None}
            if 'swimmer' not in rec:
                rec['swimmer'] = swimmer
            records.append(rec)

    # Build meet options sorted chronologically.
    # Key on (date, meet_name) — the true unique identifier for a meet.
    # Same team name can appear multiple times per year (e.g. two VSL Championship dates),
    # and the same name recurs across years, so only the date+name combo is truly unique.
    seen = set()
    meet_options_raw = []
    for r in records:
        m, d = r.get('meet',''), r.get('date','')
        if m and d:
            key = (d, m)
            if key not in seen:
                seen.add(key)
                meet_options_raw.append((d, m))
    meet_options = []
    for date, meet in sorted(meet_options_raw):
        dt = datetime.strptime(date, '%Y-%m-%d')
        meet_options.append({'value': f"{date}|{meet}", 'label': f"{dt.strftime('%b %d, %Y')} — {meet}"})

    # Serialize to compact JSON strings
    raw_data_json    = json.dumps(records,      separators=(',', ':'))
    meet_options_json = json.dumps(meet_options, separators=(',', ':'))

    # Write standalone JSON backup
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(raw_data_json)
    with open(output_file.replace('.json', '_meets.json'), 'w') as f:
        json.dump(meet_options, f, indent=2)

    # ── Inject into HTML ──────────────────────────────────────────────────────
    if not os.path.exists(html_file):
        print(f"\nWARNING: '{html_file}' not found — skipping HTML injection.")
        print(f"Standalone JSON written to {output_file}")
        return

    # Back up the HTML before touching it
    backup = html_file + ".bak"
    shutil.copy2(html_file, backup)

    with open(html_file, 'r', encoding='utf-8') as f:
        html = f.read()

    original_html = html

    # Replace RAW_DATA: matches   const RAW_DATA=[...];
    html, n_raw = re.subn(
        r'(const RAW_DATA\s*=\s*)\[.*?\](;)',
        lambda m: m.group(1) + raw_data_json + m.group(2),
        html,
        count=1,
        flags=re.DOTALL,
    )

    # Replace MEET_OPTIONS: matches   const MEET_OPTIONS=[...];
    html, n_meets = re.subn(
        r'(const MEET_OPTIONS\s*=\s*)\[.*?\](;)',
        lambda m: m.group(1) + meet_options_json + m.group(2),
        html,
        count=1,
        flags=re.DOTALL,
    )

    if n_raw == 0:
        print("WARNING: Could not find 'const RAW_DATA=[...]' in the HTML — data NOT injected.")
        print("  Make sure the HTML has exactly:  const RAW_DATA=[...]")
    if n_meets == 0:
        print("WARNING: Could not find 'const MEET_OPTIONS=[...]' in the HTML — meets NOT injected.")

    if html == original_html:
        print("\nNothing changed in the HTML (patterns not matched). Check the warnings above.")
        os.remove(backup)
        return

    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html)

    size_kb = os.path.getsize(output_file) / 1024
    unique_swimmers = len(set(r.get('swimmer','') for r in records))

    print(f"\n✓ Done!")
    print(f"  {len(records):,} records  |  {unique_swimmers:,} unique swimmers  |  {len(meet_options)} meets")
    print(f"  JSON backup:  {output_file}  ({size_kb:.0f} KB)")
    print(f"  HTML backup:  {backup}")
    print(f"  HTML updated: {html_file}")
    print(f"\n  Just refresh your browser — no copy/paste needed.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Convert PVC swim CSV to JSON and inject into index.html'
    )
    parser.add_argument('input', help='Path to the exported CSV/TXT file (e.g. /data/ResultsPVC.txt)')
    parser.add_argument('--html', default=DEFAULT_HTML_FILE,
                        help=f'Path to index.html to inject data into (default: {DEFAULT_HTML_FILE})')
    parser.add_argument('--out',  default=DEFAULT_OUTPUT_FILE,
                        help=f'Path for standalone JSON backup (default: {DEFAULT_OUTPUT_FILE})')
    args = parser.parse_args()
    convert(args.input, args.out, args.html)
