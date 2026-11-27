"""Check the saved-edition results and expansion without rebuilding a hand-written index."""
from copy import deepcopy
from html.parser import HTMLParser
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from urllib.parse import urljoin, urlsplit
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from build import ROOT, metadata
from result_pages import write_results


class Anchors(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.links, self.canonicals = [], []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a':
            self.links.append(attrs['href'])
        if tag == 'link' and attrs.get('rel') == 'canonical':
            self.canonicals.append(attrs['href'])


class ResultPages(unittest.TestCase):
    def setUp(self):
        self.folder = TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name)
        (self.path / 'data').mkdir()
        self.edition = json.loads((ROOT / 'web/data/edition.json').read_text())
        self.tool = metadata()
        self.base = 'https://coolcode.ca/spillledger/'

    def write(self):
        write_results(self.path, self.tool, deepcopy(self.edition))

    def page(self, url):
        return (self.path / url / 'index.html').read_text()

    def test_all_sitemap_records_canonical_and_local_result_links_resolve(self):
        self.write()
        urls = [row[0].text for row in ET.parse(self.path / 'sitemap.xml').getroot()]
        self.assertEqual(len(urls), len(set(urls)))
        self.assertEqual(set(urls), {self.base + str(p.parent.relative_to(self.path)) + '/' for p in self.path.rglob('index.html')})
        for url in urls:
            page = Anchors(self.page(url.removeprefix(self.base)))
            self.assertEqual(page.canonicals, [url])
            for href in page.links:
                dest = urlsplit(urljoin(url, href))
                if dest.path.startswith('/spillledger/records/'):
                    self.assertIn(self.base + dest.path.removeprefix('/spillledger/'), urls)

    def test_claimant_dates_and_shared_recovery(self):
        self.write()
        case = self.page('records/incidents/elva-m-ii-2016-11-05-richmond-british-columbia')
        self.assertIn('Steveston Harbour Authority', case)
        self.assertIn('DFO/CCG', case)
        self.assertIn('$3,266.46 recovered on 2019-07-01', case)
        self.assertEqual(case.count('$3,266.46'), 1)
        self.assertIn('<dt>Submission date</dt><dd>2017-02-09', case)
        self.assertIn('<dt>Decision date</dt><dd>2017-02-22', case)
        self.assertIn('#page=70', case)
        self.assertIn('multiple-claimants/', case)
        self.assertIn('elva-m-ii', self.page('records/stages/reported-recoveries'))

    def test_incident_without_financial_stages_and_context_link(self):
        self.write()
        bridgewater = self.page('records/places/nova-scotia/bridgewater')
        self.assertIn('cormorant-2019-07-15-bridgewater-nova-scotia#detail', bridgewater)
        self.assertIn('No financial entry published', bridgewater)
        self.assertNotIn('incidents/cormorant-2019', bridgewater)
        europe = self.page('records/incidents/europe-2023-01-21-english-bay-vancouver-british-columbia')
        self.assertIn('No recovery entry published', europe)
        self.assertIn('https://coolcode.ca/lightkeeper/records/pac-387-d-2/', europe)
        self.assertIn('#page=70', europe)

    def test_new_record_materializes_and_changed_sort_keeps_links(self):
        example = deepcopy(self.edition['records'][0])
        example.update(name='Test Ship', date='2024-02-13')
        self.edition['records'].insert(0, example)
        self.edition['count'] += 1
        self.write()
        key = 'test-ship-2024-02-13-bridgewater-nova-scotia'
        self.assertIn('incidents/' + key + '/', self.page('records/places/nova-scotia/bridgewater'))
        self.assertIn('?incident=' + key + '#detail', self.page('records/incidents/' + key))
        self.assertIn('cormorant-2015-02-27', self.page('records/stages/reported-recoveries'))
