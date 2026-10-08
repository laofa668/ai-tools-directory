"""Check directory rows and report links that are definitively gone."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import re
import sys


ROW = re.compile(r'^\| \[([^]]+)\]\((https://[^)]+)\) \| (.+) \|$')
README = Path(__file__).resolve().parents[1] / 'README.md'


def check_link(item):
    name, url = item
    request = Request(url, headers={'User-Agent': 'Mozilla/5.0 (directory link check)'})
    try:
        with urlopen(request, timeout=12) as response:
            return name, url, response.status, ''
    except HTTPError as error:
        return name, url, error.code, str(error)
    except (URLError, TimeoutError, OSError) as error:
        return name, url, None, str(error)


def main():
    links = []
    problems = []
    seen = set()

    for number, line in enumerate(README.read_text(encoding='utf-8').splitlines(), 1):
        if not line.startswith('| ['):
            continue
        match = ROW.match(line)
        if not match:
            problems.append(f'line {number}: malformed directory row')
            continue
        name, url, description = match.groups()
        if not description.strip():
            problems.append(f'line {number}: empty description')
        if url in seen:
            problems.append(f'line {number}: duplicate URL {url}')
        seen.add(url)
        links.append((name, url))

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(check_link, links))

    uncertain = []
    for name, url, status, error in results:
        if status in (404, 410):
            problems.append(f'{name}: HTTP {status} - {url}')
        elif status is None or status >= 400:
            uncertain.append(f'{name}: HTTP {status or "unknown"} - {url} ({error})')

    print(f'Checked {len(links)} links.')
    for item in uncertain:
        print(f'REVIEW: {item}')
    for item in problems:
        print(f'ERROR: {item}')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
