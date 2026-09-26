import re
from pathlib import Path
try:
    import pdfplumber
except ImportError:
    pdfplumber = None
from collections import defaultdict
from app.database import db
from app.models import Member

def parse_nhgcc_pdf(pdf_path, deduplicate=True):
    """
    Parses NHGCC database PDF containing members with columns:
    S/N | Name | Phone Number | Email Address | House Address
    Supports deduplicate=True to merge duplicate member entries into unique profiles.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found at: {pdf_path}")
    if not pdfplumber:
        raise ImportError("pdfplumber is required to parse PDF files. Install with: pip install pdfplumber")

    records = []
    with pdfplumber.open(pdf_path) as pdf:
        all_text = "\n".join([p.extract_text() or '' for p in pdf.pages])
        lines = all_text.split("\n")

    raw_entries = []
    curr = None

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if any(h in line for h in ['CONTACT DIRECTORY', 'Comprehensive Member', 'Total Records:', 'Page ']):
            continue
        if line.startswith('S/') or line.startswith('NAME PHONE') or line == 'N':
            continue

        m = re.match(r'^(\d+)\s+(.*)', line)
        if m and int(m.group(1)) <= 210:
            if curr:
                raw_entries.append(curr)
            curr = {'sn': int(m.group(1)), 'raw': m.group(2).strip()}
        elif curr:
            curr['raw'] += ' ' + line

    if curr:
        raw_entries.append(curr)

    for r in raw_entries:
        raw = r['raw']
        raw = re.sub(r'Page \d+ of \d+.*', '', raw, flags=re.IGNORECASE).strip()
        raw = re.sub(r'S/\s*N.*', '', raw).strip()

        email_match = re.search(r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', raw)
        email = email_match.group(1) if email_match else ''

        phone_match = re.search(r'(0[78901]\d{8,11}|081\d{8,11}|090\d{8,11}|070\d{8,11}|011\d{8,10})', raw)
        phone = phone_match.group(1) if phone_match else ''

        if phone_match:
            name_part = raw[:phone_match.start()].strip()
            rest = raw[phone_match.end():].strip()
        else:
            dash_match = re.search(r'\s+[—–-]\s+', raw)
            if dash_match:
                name_part = raw[:dash_match.start()].strip()
                rest = raw[dash_match.end():].strip()
            else:
                parts = raw.split()
                name_part = ' '.join(parts[:2]) if len(parts) >= 2 else raw
                rest = ' '.join(parts[2:]) if len(parts) > 2 else ''

        address_part = rest
        if email:
            address_part = address_part.replace(email, '').strip()

        address_part = re.sub(r'^[—–\-\s]+|[—–\-\s]+$', '', address_part).strip()
        name_part = re.sub(r'^[—–\-\s]+|[—–\-\s]+$', '', name_part).strip()

        title = 'Member'
        name_clean = name_part
        lower_name = name_part.lower()

        title_prefixes = [
            ('elder ', 'Elder', 'Male'),
            ('pastor ', 'Pastor', 'Male'),
            ('pst. ', 'Pastor', 'Male'),
            ('pst ', 'Pastor', 'Male'),
            ('deaconess ', 'Deaconess', 'Female'),
            ('dcn. ', 'Deacon', 'Male'),
            ('dcn ', 'Deacon', 'Male'),
            ('deacon ', 'Deacon', 'Male'),
            ('bro. ', 'Brother', 'Male'),
            ('bro ', 'Brother', 'Male'),
            ('sis. ', 'Sister', 'Female'),
            ('sis ', 'Sister', 'Female'),
            ('mr. ', 'Brother', 'Male'),
            ('mr ', 'Brother', 'Male'),
            ('mrs. ', 'Sister', 'Female'),
            ('mrs ', 'Sister', 'Female')
        ]

        gender = 'Not Specified'
        for pfx, tit, gen in title_prefixes:
            if lower_name.startswith(pfx):
                title = tit
                gender = gen
                name_clean = name_part[len(pfx):].strip()
                break

        records.append({
            'sn': r['sn'],
            'member_code': f"NHGCC-{r['sn']:04d}",
            'full_name': name_clean.title(),
            'title': title,
            'gender': gender,
            'phone': phone,
            'email': email,
            'address': address_part
        })

    if not deduplicate:
        return records

    by_name = defaultdict(list)
    for r in records:
        norm_name = ' '.join(r['full_name'].strip().split()).title()
        by_name[norm_name].append(r)

    title_priority = {
        'Pastor': 1,
        'Elder': 2,
        'Deacon': 3,
        'Deaconess': 4,
        'Brother': 5,
        'Sister': 6,
        'Member': 7
    }

    deduped = []
    for idx, (name, entries) in enumerate(by_name.items(), 1):
        sorted_by_title = sorted(entries, key=lambda x: title_priority.get(x['title'], 99))
        best_title = sorted_by_title[0]['title']

        genders = [e['gender'] for e in entries if e['gender'] != 'Not Specified']
        best_gender = genders[0] if genders else 'Not Specified'

        phones = list(dict.fromkeys(e['phone'] for e in entries if e['phone']))
        best_phone = ', '.join(phones) if phones else ''

        emails = list(dict.fromkeys(e['email'] for e in entries if e['email']))
        best_email = emails[0] if emails else ''

        addresses = [e['address'] for e in entries if e['address']]
        best_address = max(addresses, key=len) if addresses else ''

        original_sns = [str(e['sn']) for e in entries]
        notes = f"Original PDF S/N: {', '.join(original_sns)}" if len(entries) > 1 else ''

        deduped.append({
            'sn': entries[0]['sn'],
            'member_code': f"NHGCC-{idx:04d}",
            'full_name': name,
            'title': best_title,
            'gender': best_gender,
            'phone': best_phone,
            'email': best_email,
            'address': best_address,
            'notes': notes
        })

    return deduped

def import_pdf_to_database(pdf_path, force=False, deduplicate=True):
    """Imports parsed members into the database keyed by unique member_code."""
    members_data = parse_nhgcc_pdf(pdf_path, deduplicate=deduplicate)
    count_added = 0
    count_updated = 0

    for item in members_data:
        existing = Member.query.filter_by(member_code=item['member_code']).first()
        if not existing:
            parts = item['full_name'].split()
            first_name = parts[0] if len(parts) > 0 else ''
            last_name = parts[1] if len(parts) > 1 else ''

            new_member = Member(
                member_code=item['member_code'],
                full_name=item['full_name'],
                first_name=first_name,
                last_name=last_name,
                title=item['title'],
                gender=item['gender'],
                phone=item['phone'],
                email=item['email'],
                address=item['address'],
                notes=item.get('notes', ''),
                department='Congregation',
                status='Active'
            )
            db.session.add(new_member)
            count_added += 1
        elif force:
            existing.full_name = item['full_name']
            existing.title = item['title']
            existing.gender = item['gender']
            existing.phone = item['phone'] or existing.phone
            existing.email = item['email'] or existing.email
            existing.address = item['address'] or existing.address
            if item.get('notes'):
                existing.notes = item['notes']
            count_updated += 1

    db.session.commit()
    return {
        'total': len(members_data),
        'added': count_added,
        'updated': count_updated
    }
