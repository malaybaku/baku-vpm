from contextlib import redirect_stdout
from io import BytesIO, StringIO
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import build_listing as build

NAME = 'com.example.test'
URL = 'https://example.test/package.zip'


def manifest(version='1.0.0'):
    return dict(name=NAME, version=version, displayName='Test package',
                author={'name': 'Author'}, vpmDependencies={'com.example.dep': '>=1.0.0'})


def zip_bytes(value, filename='package.json'):
    output = BytesIO()
    with ZipFile(output, 'w') as archive:
        archive.writestr(filename, json.dumps(value))
    return output.getvalue()


def source():
    return dict(name='Test listing', id='io.github.test.vpm', url='https://example.test/index.json',
                author={'name': 'Author'}, packages=[dict(name=NAME, releases=[URL])])


class ListingTests(unittest.TestCase):
    def build(self, src=None, previous=None, value=None):
        with redirect_stdout(StringIO()):
            return build.build_listing(src or source(), previous or {}, lambda *args: zip_bytes(value or manifest()))

    def test_manifest_and_hash(self):
        data = zip_bytes(manifest())
        result = build.read_release(data, URL, NAME)
        self.assertEqual(result['url'], URL)
        self.assertEqual(result['zipSHA256'], build.hashlib.sha256(data).hexdigest())
        self.assertEqual(result['vpmDependencies'], {'com.example.dep': '>=1.0.0'})
        self.assertNotIn('email', result['author'])

    def test_previous_versions_survive_source_removal(self):
        old = self.build(value=manifest('0.9.0'))
        updated = self.build(previous=old)
        self.assertEqual(set(updated['packages'][NAME]['versions']), {'0.9.0', '1.0.0'})
        empty = source()
        empty['packages'] = []
        kept = self.build(empty, previous=updated)
        self.assertEqual(kept['packages'], updated['packages'])

    def test_repeated_version_is_idempotent_but_changes_are_rejected(self):
        old = self.build()
        self.assertEqual(old, self.build(previous=old))
        changed = manifest()
        changed['description'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'Published version changed'):
            self.build(previous=old, value=changed)

    def test_listing_identity_cannot_change(self):
        previous = self.build()
        previous['id'] = 'other'
        with self.assertRaisesRegex(ValueError, 'identity'):
            self.build(previous=previous)

    def test_bad_zip_and_manifest_are_rejected(self):
        for data in (b'not a zip', zip_bytes(manifest(), 'folder/package.json'),
                     zip_bytes(dict(manifest(), name='wrong')), zip_bytes(dict(manifest(), version='01.0.0'))):
            with self.subTest(data=data[:10]), self.assertRaises(ValueError):
                build.read_release(data, URL, NAME)
        with self.assertRaisesRegex(ValueError, 'Duplicate JSON key'):
            build.decode_json(b'{"name":"one","name":"two"}')

    def test_unpublished_zip_fails_without_partial_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'Website').mkdir()
            (root / 'Website/index.html').write_text('$packages', encoding='utf-8')
            (root / 'source.json').write_text(json.dumps(source()), encoding='utf-8')
            (root / 'previous.json').write_text('{}', encoding='utf-8')
            out = root / 'dist'
            args = ['build_listing.py', '--source', str(root / 'source.json'), '--previous', str(root / 'previous.json'), '--output', str(out)]
            with patch.object(sys, 'argv', args), patch.object(build, 'fetch', side_effect=HTTPError(URL, 404, 'missing', {}, None)), redirect_stdout(StringIO()):
                with self.assertRaises(HTTPError):
                    build.main()
            self.assertFalse(out.exists())

    def test_previous_404_only_is_treated_as_first_publish(self):
        with patch.object(build, 'fetch', side_effect=HTTPError(URL, 404, 'missing', {}, None)), redirect_stdout(StringIO()):
            self.assertEqual(build.load_previous(URL), {})
        with patch.object(build, 'fetch', side_effect=HTTPError(URL, 503, 'unavailable', {}, None)):
            with self.assertRaises(HTTPError):
                build.load_previous(URL)

    def test_semver_order(self):
        values = ['1.0.0', '1.0.0-beta.10', '1.0.0-beta.2', '1.0.0-alpha', '1.0.0-2', '1.0.0-1']
        self.assertEqual(sorted(values, key=build.version_key), list(reversed(values)))
        for invalid in ('v1.0.0', '1.0', '1.0.0-01', '1.00.0'):
            with self.assertRaises(ValueError):
                build.version_key(invalid)

    def test_html_escapes_data_and_prefers_stable(self):
        listing = self.build(value=dict(manifest(), displayName='<script>bad()</script>', description='"<img src=x>'))
        listing['packages'][NAME]['versions']['2.0.0-beta.1'] = manifest('2.0.0-beta.1')
        src = source()
        src['name'] = '<bad>'
        rendered = build.render_page('$listing_name $packages $add_url $author $info_link', src, listing)
        self.assertNotIn('<script>', rendered)
        self.assertNotIn('<img', rendered)
        self.assertIn('&lt;script&gt;', rendered)
        self.assertIn('&lt;bad&gt;', rendered)
        self.assertNotIn('2.0.0-beta.1', rendered)
        self.assertIn('https%3A%2F%2Fexample.test', rendered)

    def test_unsafe_urls_are_rejected(self):
        for url in ('javascript:alert(1)', 'http://example.test', 'file:///tmp/package.zip', 'https://user:pass@example.test/a'):
            with self.assertRaises(ValueError):
                build.https_url(url)
        listing = self.build(value=dict(manifest(), documentationUrl='javascript:alert(1)'))
        with self.assertRaises(ValueError):
            build.render_page('$packages', source(), listing)

    def test_end_to_end_outputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'Website').mkdir()
            template = (Path(__file__).resolve().parents[1] / 'Website/index.html').read_text(encoding='utf-8-sig')
            (root / 'Website/index.html').write_text(template, encoding='utf-8')
            (root / 'source.json').write_text(json.dumps(source()), encoding='utf-8')
            (root / 'previous.json').write_text('{}', encoding='utf-8')
            args = ['build_listing.py', '--source', str(root / 'source.json'), '--previous', str(root / 'previous.json'), '--output', str(root / 'dist')]
            with patch.object(sys, 'argv', args), patch.object(build, 'fetch', return_value=zip_bytes(manifest())), redirect_stdout(StringIO()):
                build.main()
            listing = json.loads((root / 'dist/index.json').read_text(encoding='utf-8'))
            self.assertEqual(listing['author'], 'Author')
            self.assertIn('1.0.0', listing['packages'][NAME]['versions'])
            page = (root / 'dist/index.html').read_text(encoding='utf-8')
            self.assertNotIn('$packages', page)
            self.assertNotIn('{{', page)
            self.assertIn('Test package', page)
            self.assertTrue((root / 'dist/.nojekyll').exists())


if __name__ == '__main__':
    unittest.main()
