from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup


def rewrite_urls(content: bytes, target_url: str):
    """
    Replace all relative URLs in HTML with absolute URLs
    pointing to the original target site.
    """
    origin = f"{urlparse(target_url).scheme}://{urlparse(target_url).netloc}"
    soup = BeautifulSoup(content, "html.parser")

    assets = {
        'img': 'src',
        'script': 'src',
        'link': 'href',
        'a': 'href',
        'form': 'action',
        'video': 'src',
        'source': 'src',
    }

    for tag, attr in assets.items():
        for element in soup.find_all():
            url = element.get(attr)
            if not url or url.startswith('data:') or url.startswith('#'):
                continue
            
            absolute = urljoin(origin, url)
            element[attr] = absolute

    return str(soup).encode()
