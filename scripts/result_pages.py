"""Build incident and comparison pages from the same edition as the explorer."""
from collections import defaultdict
from datetime import date
from html import escape
import json
import posixpath
import re
import unicodedata
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET


BLANK = {'', '-', '–', '—'}
MONEY = re.compile(r'\$[\d,]+(?:\.\d+)?')
DATE = re.compile(r'\d{4}-\d{2}-\d{2}')
STAGES = {
    'reported-recoveries': ('Amounts recovered', 'The fund gives a dollar amount recovered for each incident below. A recovery applies to the incident as a whole.'),
    'multiple-claimants': ('Incidents with multiple claimants', 'Compare the amounts submitted and the decision for each claimant. The fund records recovery once for the incident.'),
    'assessments-ongoing': ('Claims under assessment', 'These claims were under assessment when the report was compiled. The figures are the amounts submitted by the claimants.'),
    'amounts-offered': ('Claims with published offers', 'Compare each claimant’s submission and the amount the fund offered. An offer records a decision. Payment and recovery are separate steps.'),
}
LIGHTKEEPER_CONTEXT = {'europe-2023-01-21-english-bay-vancouver-british-columbia':
                       ('English Bay Anchorage East', 'https://coolcode.ca/lightkeeper/records/pac-387-d-2/')}
# The archived PDF wraps these locations across lines within the incident cell.
# Rejoin only the printed pairs, leaving vessel types and spill details alone.
WRAPPED_LOCATIONS = {('Rushbrook Harbour,', 'Prince Rupert'), ('Discovery Harbour Marina,', 'Campbell River'),
                     ('Dusenbury Island, Pender', 'Harbour'), ('Cooper’s Cove', 'Sooke Basin'),
                     ('Hecate Channel, Tahsis', 'Narrows')}


def e(value):
    return escape(str(value), quote=True)


def slug(text):
    ascii_text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode()
    value = re.sub(r'[^a-z0-9]+', '-', ascii_text.lower()).strip('-')
    if not value:
        raise ValueError(f'Cannot create a result URL for {text!r}')
    return value


def entry(lines):
    text = ' '.join(lines).strip()
    return '' if text in BLANK else text


def money(lines):
    match = MONEY.search(entry(lines))
    return match[0] if match else ''


def row_date(lines):
    return next((s for s in lines if DATE.fullmatch(s)), '')


def claimant(claim):
    lines = claim['submission']
    stamp = row_date(lines)
    return ' '.join(lines[lines.index(stamp) + 1:]) if stamp else ''


def profile_path(r):
    return 'records/incidents/' + r['key'] + '/'


def province_path(name):
    return 'records/provinces/' + slug(name) + '/'


def place_path(province, place):
    return 'records/places/' + slug(province) + '/' + slug(place) + '/'


def stage_path(key):
    return 'records/stages/' + key + '/'


def link(href, label):
    return f'<a href="{e(href)}">{e(label)}</a>'


def relative(path, target):
    url = posixpath.relpath(target or '.', path)
    return ('./' if url == '.' else url + '/')


def local(path, target, label):
    return link(relative(path, target), label)


def selection(path, r):
    return link(relative(path, '') + '?incident=' + r['key'] + '#detail', 'Open this incident in the explorer')


def source(edition, page):
    return link(edition['source'] + '#page=' + str(page), f'Annual report, PDF p. {page}')


def fiscal(edition):
    return f"{edition['end'] - 1}–{str(edition['end'])[-2:]}"


def stage_keys(r):
    keys = []
    if money(r['recovery']):
        keys.append('reported-recoveries')
    if len({claimant(c) for c in r['claims'] if claimant(c)}) > 1:
        keys.append('multiple-claimants')
    if any(entry(c['decision']).casefold() == 'assessment ongoing' for c in r['claims']):
        keys.append('assessments-ongoing')
    if any(money(c['decision']) for c in r['claims']):
        keys.append('amounts-offered')
    return keys


def summary(r):
    if len(r['claims']) > 1:
        people = [claimant(c) for c in r['claims'] if claimant(c)]
        listed = ', '.join(people)
        return f"The fund lists {len(r['claims'])} claim records" + (f', including {listed}.' if listed else '.')
    claim = r['claims'][0]
    parts = []
    amount, offer, recovery = money(claim['submission']), money(claim['decision']), money(r['recovery'])
    if amount:
        parts.append(f'{amount} claimed')
    elif claimant(claim):
        parts.append(f'Claim submitted by {claimant(claim)}')
    if offer:
        parts.append(f'{offer} offered')
    elif entry(claim['decision']):
        parts.append(entry(claim['decision']))
    if recovery:
        parts.append(f'{recovery} recovered')
    return ' · '.join(parts) + '.' if parts else 'The report gives no amount for a claim, offer or recovery.'


def enrich(edition):
    records = edition['records']
    if len(records) != edition['count'] or not records:
        raise ValueError('The incident count must match the nonempty edition')
    if urlsplit(edition['source']).scheme != 'https':
        raise ValueError('Expected an HTTPS annual report URL')
    date.fromisoformat(edition['retrieved'])
    keys = set()
    for r in records:
        date.fromisoformat(r['date'])
        if not r['claims'] or r['description'][0] != r['place']:
            raise ValueError('Unexpected incident or claim layout')
        joined = tuple(r['description'][:2]) in WRAPPED_LOCATIONS
        if joined:
            r['place'] = ' '.join(r['description'][:2])
            r['description'] = [r['place'], *r['description'][2:]]
        key = slug(' '.join((r['name'], r['date'], r['place'], r['province'])))
        if key in keys:
            raise ValueError(f'Ambiguous incident URL: {key}')
        keys.add(key)
        r['key'] = key
        r['has_profile'] = key in LIGHTKEEPER_CONTEXT or bool(entry(r['recovery']) or any(entry(c['submission']) or entry(c['decision']) for c in r['claims']))


def group_list(path, items):
    return '<ul class="group-list">' + ''.join(f'<li>{local(path, target, label)} <span>{count}</span></li>' for target, label, count in items) + '</ul>'


def case_list(path, records, edition, stage=None):
    items = []
    for r in sorted(records, key=lambda row: (row['date'], row['name']), reverse=True):
        label = f"{r['name']} · {r['place']} · {r['date']}"
        heading = local(path, profile_path(r), label) if r['has_profile'] else e(label)
        if stage == 'reported-recoveries':
            text = f"{money(r['recovery'])} recovered" + (f" on {row_date(r['recovery'])}." if row_date(r['recovery']) else '.')
        elif stage == 'assessments-ongoing':
            text = ' '.join(f"{entry(c['submission'])}." for c in r['claims'] if entry(c['decision']).casefold() == 'assessment ongoing')
        elif stage == 'amounts-offered':
            text = ' '.join(f"{claimant(c)}: {money(c['submission']) or 'amount unspecified'} claimed, {money(c['decision'])} offered." for c in r['claims'] if money(c['decision']))
        else:
            text = summary(r)
        details = source(edition, r['page'])
        if not r['has_profile']:
            text = ' · '.join([*r['description'][1:], *(dict.fromkeys(c['status'] for c in r['claims']))]) + '. No financial entry published.'
            details += ' · ' + selection(path, r)
        items.append(f'<li id="{r["key"]}"><strong>{heading}</strong><p>{e(text)}</p>{details}</li>')
    return '<ul class="case-list">' + ''.join(items) + '</ul>'


def profile(path, r, edition, neighbours, stages):
    province, place = r['province'], r['place']
    body = [f'<p class="actions">{selection(path, r)}</p><p>{e(" · ".join(r["description"][1:]))}</p>',
            f'<section><h2>Claim and decision records</h2><p>Amounts are in Canadian dollars. File status is as printed in the {fiscal(edition)} report.</p>']
    for i, c in enumerate(r['claims'], 1):
        title = claimant(c) or f'Claim record {i}'
        submission_date = row_date(c['submission'])
        submitted = entry(c['submission'][:c['submission'].index(submission_date)]) if submission_date else entry(c['submission'])
        decision_date = row_date(c['decision'])
        decision = entry([s for s in c['decision'] if s != decision_date])
        rows = [('Amount claimed', submitted or 'No entry published')]
        if submission_date:
            rows.append(('Submission date', submission_date))
        rows.append(('Offer or decision', decision or 'No entry published'))
        if decision_date:
            rows.append(('Decision date', decision_date))
        rows.append(('File status', c['status']))
        facts = ''.join(f'<dt>{e(k)}</dt><dd>{e(v)}</dd>' for k, v in rows)
        body.append(f'<article class="claim"><h3>{e(title)}</h3><dl>{facts}</dl>{source(edition, c["page"])}</article>')
    recovered, recovered_on = money(r['recovery']), row_date(r['recovery'])
    recovery = f'{recovered} recovered on {recovered_on}' if recovered and recovered_on else entry(r['recovery'])
    body.append(f'</section><section><h2>Recovery for the incident</h2><p>{e(recovery or "No recovery entry published")}.</p>')
    if len(r['claims']) > 1:
        body.append('<p>The recovery entry covers all claimants together.</p>')
    body.append(source(edition, r['page']) + '</section><section><h2>Compare records</h2>')
    comparisons = [(province_path(province), f'{province} report section')]
    if len(neighbours) > 1:
        comparisons.append((place_path(province, place), f'{place} incidents ({len(neighbours)})'))
    categories = stage_keys(r)
    comparisons.extend((stage_path(k), STAGES[k][0]) for k in categories)
    body.append('<ul>' + ''.join(f'<li>{local(path, dest, text)}</li>' for dest, text in comparisons) + '</ul>')
    others = [n for n in neighbours if n['key'] != r['key']]
    if others:
        body.append(f'<h3>Also recorded at {e(place)}</h3>' + case_list(path, others, edition))
    elif categories:
        group = min(categories, key=lambda k: len(stages[k]))
        peers = [s for s in stages[group] if s['key'] != r['key']]
        peers.sort(key=lambda s: (s['province'] != province, s['name'], s['date'], s['key']))
        if peers:
            body.append(f'<h3>Compare {e(STAGES[group][0].lower())}</h3>' + case_list(path, peers[:2], edition, group))
    if r['key'] in LIGHTKEEPER_CONTEXT:
        light, href = LIGHTKEEPER_CONTEXT[r['key']]
        body.append('<h3>Navigation in the same bay</h3><p>Lightkeeper lists ' + link(href, light) + ', a navigation aid on English Bay. Its record describes the light independently of this incident.</p>')
    body.append('</section>')
    return ''.join(body)


def write_results(stage, tool, edition):
    enrich(edition)
    records = edition['records']
    provinces, places, stages = defaultdict(list), defaultdict(list), defaultdict(list)
    pages = set()
    for r in records:
        provinces[r['province']].append(r)
        places[r['province'], r['place']].append(r)
        for key in stage_keys(r):
            stages[key].append(r)
    base = 'https://coolcode.ca' + tool['url']
    index = 'records/'
    year = fiscal(edition)

    def write(path, title, heading, desc, body):
        if path in pages:
            raise ValueError(f'Duplicate result URL: {path}')
        pages.add(path)
        root = relative(path, '')
        directory = local(path, index, 'Browse all incident records') if path != index else ''
        markup = f'''<!doctype html><html lang="en-CA"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} · Spill Ledger</title><meta name="description" content="{e(desc)}"><link rel="canonical" href="{e(base + path)}">
<link rel="stylesheet" href="{root}style.css"><script defer src="/assets/tool-metrics.js" referrerpolicy="no-referrer"></script></head>
<body data-tool-id="spillledger"><a class="skip" href="#record">Skip to record</a><header><div class="wrap"><nav aria-label="Navigation">{link(root, 'Spill Ledger')}{directory}{link('https://coolcode.ca/', 'CoolCode.ca')}</nav><div class="mast"><h1>{e(heading)}</h1><p>{e(desc)}</p></div></div></header>
<main id="record" class="wrap record">{body}</main><footer class="wrap"><p>{link(edition['source'], f'Ship-source Oil Pollution Fund annual report, {year}')} · Source checked {e(edition['retrieved'])} UTC.</p><p>The general-process table includes preventive responses and incidents dating from before the report year.</p><p>{link(root + '#sources', 'Sources and method')} · {link('https://coolcode.ca/report/?tool=spillledger', 'Report a correction')}</p></footer></body></html>'''
        folder = stage / path
        folder.mkdir(parents=True, exist_ok=True)
        (folder / 'index.html').write_text(markup, encoding='utf-8')

    def place_links(path, province=None):
        items = [(place_path(region, place), place, len(rows)) for (region, place), rows in sorted(places.items()) if len(rows) > 1 and (province is None or province == region)]
        return '<section><h2>Locations with multiple incidents</h2>' + group_list(path, items) + '</section>' if items else ''

    for r in records:
        if not r['has_profile']:
            continue
        path = profile_path(r)
        name = f"{r['name']} · {r['place']} · {r['date']}"
        desc = f"{r['province']} report section. {summary(r)}"
        write(path, name + ' marine incident record', name, desc, profile(path, r, edition, places[r['province'], r['place']], stages))
    for province, rows in provinces.items():
        path = province_path(province)
        heading = f'{province} marine incident records'
        desc = f'{len(rows)} incidents appear in the {province} section of the {year} annual report. Compare the vessels, incident dates and published financial records.'
        write(path, heading, heading, desc, place_links(path, province) + '<section><h2>Incidents by date</h2>' + case_list(path, rows, edition) + '</section>')
    for (province, place), rows in places.items():
        if len(rows) < 2:
            continue
        path = place_path(province, place)
        heading = f'Marine incident records for {place}'
        desc = f'{len(rows)} incidents list {place} in the {province} section of the {year} report. Compare the incident dates, submitted claims and recorded outcomes.'
        write(path, heading + ' · ' + province, heading, desc, '<section><h2>Compare incidents</h2>' + case_list(path, rows, edition) + '</section><p>' + local(path, province_path(province), f'All {province} records') + '</p>')
    for key, rows in stages.items():
        path = stage_path(key)
        heading, explanation = STAGES[key]
        desc = f'{len(rows)} incidents in the {year} BC and Nova Scotia report sections. {explanation}'
        write(path, heading + ' in marine pollution records', heading, desc, '<section><h2>Compare the records</h2>' + case_list(path, rows, edition, key) + '</section>')
    example = next((r for r in records if (r['name'], r['date']) == ('Cormorant', '2015-02-27') and r['has_profile']), next((r for r in records if r['has_profile']), None))
    body = ''
    if example:
        body = '<section class="feature"><h2>Start with one incident</h2><p>' + local(index, profile_path(example), example['name'] + ' at ' + example['place']) + ' · ' + e(summary(example)) + '</p></section>'
    body += '<section><h2>Choose a report section</h2>' + group_list(index, [(province_path(p), p, len(rs)) for p, rs in sorted(provinces.items())]) + '</section>'
    body += '<section><h2>Compare financial stages</h2>' + group_list(index, [(stage_path(k), STAGES[k][0], len(stages[k])) for k in STAGES if stages.get(k)]) + '</section>' + place_links(index)
    body += '<section><h2>Incidents by date</h2>' + case_list(index, records, edition) + '</section>'
    write(index, 'Marine pollution claims by incident, place and financial stage', 'Marine incident records', f'Browse {len(records)} incidents in the {year} federal compensation report for British Columbia and Nova Scotia. Start with a vessel, a location or a financial stage.', body)
    sitemap = ET.Element('urlset', xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
    for p in sorted(pages):
        ET.SubElement(ET.SubElement(sitemap, 'url'), 'loc').text = base + p
    ET.ElementTree(sitemap).write(stage / 'sitemap.xml', encoding='utf-8', xml_declaration=True)
    (stage / 'data/edition.json').write_text(json.dumps(edition, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    return example
