#!/usr/bin/env python3
import re
import sys
import base64
import mimetypes
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


def fetch_text(url):
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    return r


def inline_stylesheets(soup, base_url):
    for link in list(soup.find_all('link', rel=lambda v: v and 'stylesheet' in v)):
        href = link.get('href')
        if not href:
            continue
        full = urljoin(base_url, href)
        try:
            r = fetch_text(full)
            style = soup.new_tag('style')
            style.string = r.text
            link.replace_with(style)
        except Exception:
            continue


def inline_scripts(soup, base_url):
    for script in list(soup.find_all('script', src=True)):
        src = script.get('src')
        full = urljoin(base_url, src)
        try:
            r = fetch_text(full)
            new = soup.new_tag('script')
            new.string = r.text
            script.replace_with(new)
        except Exception:
            continue


def to_data_uri(url, base_url):
    full = urljoin(base_url, url)
    try:
        r = requests.get(full, timeout=30)
        r.raise_for_status()
        ctype = r.headers.get('Content-Type') or mimetypes.guess_type(full)[0] or 'application/octet-stream'
        data = base64.b64encode(r.content).decode('ascii')
        return f'data:{ctype};base64,{data}'
    except Exception:
        return url


def inline_images(soup, base_url):
    for img in list(soup.find_all('img')):
        src = img.get('src')
        if not src or src.startswith('data:'):
            continue
        img['src'] = to_data_uri(src, base_url)


def inline_css_urls(text, base_url):
    def repl(m):
        url = m.group(1).strip('"\'')
        if url.startswith('data:'):
            return f'url({url})'
        data = to_data_uri(url, base_url)
        return f'url({data})'

    return re.sub(r'url\(([^)]+)\)', repl, text, flags=re.I)


def inline_css_in_style_tags(soup, base_url):
    for style in soup.find_all('style'):
        if style.string:
            style.string = inline_css_urls(style.string, base_url)


def inline_style_attributes(soup, base_url):
    for tag in soup.find_all(True):
        style = tag.get('style')
        if style:
            tag['style'] = inline_css_urls(style, base_url)


def make_single_file(url, outpath):
    r = fetch_text(url)
    soup = BeautifulSoup(r.text, 'html.parser')

    inline_stylesheets(soup, url)
    inline_scripts(soup, url)
    inline_images(soup, url)
    inline_css_in_style_tags(soup, url)
    inline_style_attributes(soup, url)

    html = str(soup)
    with open(outpath, 'w', encoding='utf-8') as f:
        f.write(html)


def main():
    if len(sys.argv) < 3:
        print('Usage: mirror_page.py <URL> <output.html>')
        sys.exit(2)
    url = sys.argv[1]
    out = sys.argv[2]
    print('Fetching and inlining resources...')
    make_single_file(url, out)
    print('Written', out)


if __name__ == '__main__':
    main()
