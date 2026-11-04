"""Generate a VPM listing and static page using only the Python standard library."""
import argparse
import copy
import hashlib
import html
import io
import json
from pathlib import Path
import re
from string import Template
from urllib.error import HTTPError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen
from zipfile import ZipFile, BadZipFile

VERSION = re.compile(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?')
ZIP_LIMIT = 100 * 1024 * 1024
JSON_LIMIT = 10 * 1024 * 1024
MANIFEST_LIMIT = 1024 * 1024


def version_key(version):
    match = VERSION.fullmatch(version) if isinstance(version, str) else None
    if not match:
        raise ValueError(f'Invalid SemVer: {version!r}')
    pre = match[4]
    identifiers = []
    for part in pre.split('.') if pre else []:
        if part.isdigit():
            if len(part) > 1 and part.startswith('0'):
                raise ValueError(f'Invalid numeric prerelease: {version}')
            identifiers.append((0, int(part)))
        else:
            identifiers.append((1, part))
    return tuple(map(int, match.group(1, 2, 3))) + (pre is None, tuple(identifiers))


def https_url(url):
    if not isinstance(url, str):
        raise ValueError('URL must be a string')
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError(f'Expected an HTTPS URL without credentials: {url!r}')
    return url


def fetch(url, limit):
    request = Request(https_url(url), headers={'User-Agent': 'baxter-vpm-listing-builder'})
    with urlopen(request, timeout=30) as response:
        https_url(response.url)
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError(f'Download exceeds {limit} bytes: {url}')
    return data


def decode_json(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f'Duplicate JSON key: {key}')
            result[key] = value
        return result
    return json.loads(data.decode('utf-8-sig'), object_pairs_hook=unique)


def require_text(obj, key):
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'Missing or invalid {key}')
    return value


def validate_manifest(manifest, expected_name):
    if not isinstance(manifest, dict) or manifest.get('name') != expected_name:
        raise ValueError(f'ZIP manifest package name does not match {expected_name}')
    version_key(require_text(manifest, 'version'))
    require_text(manifest, 'displayName')
    author = manifest.get('author')
    if not isinstance(author, dict):
        raise ValueError('Manifest author must be an object')
    require_text(author, 'name')
    for key in ('dependencies', 'vpmDependencies'):
        values = manifest.get(key, {})
        if not isinstance(values, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in values.items()):
            raise ValueError(f'Invalid {key}')


def read_release(data, url, name):
    try:
        with ZipFile(io.BytesIO(data)) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                raise ValueError('ZIP contains duplicate entries')
            if 'package.json' not in names:
                raise ValueError('ZIP must contain package.json at its root')
            info = archive.getinfo('package.json')
            if info.file_size > MANIFEST_LIMIT:
                raise ValueError('ZIP package.json is too large')
            manifest = decode_json(archive.read(info))
    except BadZipFile as error:
        raise ValueError('Invalid package ZIP') from error
    validate_manifest(manifest, name)
    manifest['url'] = https_url(url)
    manifest['zipSHA256'] = hashlib.sha256(data).hexdigest()
    return manifest


def build_listing(source, previous, download=None):
    download = download or fetch
    for key in ('name', 'id', 'url'):
        require_text(source, key)
    https_url(source['url'])
    author = source.get('author')
    if not isinstance(author, dict):
        raise ValueError('Source author must be an object')
    require_text(author, 'name')
    if source.get('githubRepos'):
        raise ValueError('githubRepos is not supported; specify explicit packages[].releases ZIP URLs')
    if previous and (previous.get('id') != source['id'] or previous.get('url') != source['url']):
        raise ValueError('Previous listing identity does not match source')
    packages = copy.deepcopy(previous.get('packages', {}))
    if not isinstance(packages, dict):
        raise ValueError('Invalid previous packages')
    for name, package in packages.items():
        for version, manifest in package['versions'].items():
            validate_manifest(manifest, name)
            https_url(require_text(manifest, 'url'))
            if version != manifest['version']:
                raise ValueError('Previous version key does not match manifest')
    entries = source.get('packages', [])
    if not isinstance(entries, list):
        raise ValueError('Source packages must be an array')
    for entry in entries:
        name = require_text(entry, 'name')
        releases = entry.get('releases')
        if not isinstance(releases, list):
            raise ValueError('releases must be an array')
        for url in releases:
            https_url(url)
            print(f'Reading {url}')
            manifest = read_release(download(url, ZIP_LIMIT), url, name)
            versions = packages.setdefault(name, {'versions': {}})['versions']
            version = manifest['version']
            if version in versions and versions[version] != manifest:
                raise ValueError(f'Published version changed: {name} {version}')
            versions[version] = manifest
    return dict(name=source['name'], id=source['id'], url=source['url'],
                author=author['name'], packages=packages)


def render_page(template, source, listing):
    escape = lambda value: html.escape(str(value), quote=True)
    cards = []
    for name, package in sorted(listing['packages'].items()):
        manifests = list(package['versions'].values())
        stable = [m for m in manifests if version_key(m['version'])[3]]
        if not manifests:
            continue
        latest = max(stable or manifests, key=lambda m: version_key(m['version']))
        links = []
        for label, url in (('導入方法・対応範囲', latest.get('documentationUrl')),):
            if url:
                links.append(f'<a href="{escape(https_url(url))}">{label}</a>')
        cards.append('<section><h2>' + escape(latest['displayName']) + '</h2><p>'
                     + escape(latest.get('description', '')) + '</p><p><code>' + escape(name)
                     + '</code> / ' + escape(latest['version']) + '</p><p>' + ' / '.join(links) + '</p></section>')
    author_url = source['author'].get('url')
    author = escape(source['author']['name'])
    if author_url:
        author = f'<a href="{escape(https_url(author_url))}">{author}</a>'
    info = source.get('infoLink', {})
    info_link = ''
    if info.get('url'):
        info_link = f'<a href="{escape(https_url(info["url"]))}">{escape(info.get("text", "GitHub"))}</a>'
    return Template(template).substitute(
        listing_name=escape(source['name']), description=escape(source.get('description', '')),
        listing_url=escape(source['url']),
        add_url=escape('vcc://vpm/addRepo?url=' + quote(source['url'], safe='')),
        packages='\n'.join(cards) or '<p>パッケージ公開準備中です。</p>',
        author=author, info_link=info_link)


def load_previous(url):
    try:
        return decode_json(fetch(url, JSON_LIMIT))
    except HTTPError as error:
        if error.code == 404:
            print('No published listing yet (HTTP 404); starting a new listing')
            return {}
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('source.json'))
    parser.add_argument('--previous', type=Path, help='Use a local previous listing instead of the published URL')
    parser.add_argument('--output', type=Path, default=Path('dist'))
    args = parser.parse_args()
    source = decode_json(args.source.read_bytes())
    previous = decode_json(args.previous.read_bytes()) if args.previous else load_previous(source['url'])
    listing = build_listing(source, previous)
    template = (args.source.parent / 'Website' / 'index.html').read_text(encoding='utf-8-sig')
    page = render_page(template, source, listing)
    # Generate everything before writing, so a failed download cannot publish a partial listing.
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'index.json').write_text(json.dumps(listing, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (args.output / 'index.html').write_text(page, encoding='utf-8')
    (args.output / '.nojekyll').write_text('', encoding='utf-8')
    print(f'Generated {args.output}/index.json and index.html')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError) as error:
        raise SystemExit(f'Listing generation failed: {error}')
