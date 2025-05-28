
import requests
from bs4 import BeautifulSoup
import re
import copy

def log(msg):
    print("[LOG]", msg)

def safe_request(url, timeout=15):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://google.com",  # Optional: makes it look more human
    }

    try:
        res = requests.get(url, timeout=timeout, headers=headers)
        res.raise_for_status()
        return res
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to fetch {url} — {e}")
        return None


def get_search_results(query):
    search_url = f"https://movies4u.show/?s={query.replace(' ', '+')}"
    log(f"Searching: {search_url}")
    res = safe_request(search_url)
    if not res:
        return None
    soup = BeautifulSoup(res.text, 'html.parser')
    results = []
    for post in soup.select('article.post'):
        title_tag = post.select_one('h3.entry-title a')
        if title_tag:
            results.append((title_tag.text.strip(), title_tag['href']))
    return results

def get_linkz_url(movie_url):
    log(f"Opening movie page: {movie_url}")
    res = safe_request(movie_url)
    if not res:
        return None
    soup = BeautifulSoup(res.text, 'html.parser')
    season_match = re.search(r'season-(\d+)(?:-(\d+))?', movie_url)

    if season_match:
        season1 = season_match.group(1)
        season2 = season_match.group(2)
        if season2 and int(season2) > int(season1) and int(season2) - int(season1) <= 20:
            log(f"🟠 Detected multiple seasons: Season {season1} to {season2}")
            seasons_dict = {}
            for h4_tag in soup.find_all('h4'):
                season_text_match = re.search(r'season\s*(\d+)', h4_tag.text.lower())
                if not season_text_match:
                    continue
                season_number = season_text_match.group(1)
                download_div = h4_tag.find_next('div', class_='downloads-btns-div')
                if not download_div:
                    continue
                zip_link = download_div.find('a', class_='btn btn-zip')
                regular_link = download_div.find('a', class_='btn')
                if zip_link:
                    download_link = zip_link['href']
                elif regular_link:
                    download_link = regular_link['href']
                else:
                    continue
                seasons_dict[season_number] = download_link
            return seasons_dict
        else:
            log(f"🟢 Detected single season: Season {season1}")
            for btn in soup.select('a.btn-zip'):
                if "ZIP" in btn.text:
                    return season1, btn['href']
            for btn in soup.select('a.btn'):
                href = btn.get('href', '')
                if 'linkz.mom' in href:
                    return season1, href
            return None
    else:
        log("⚪ No 'season' pattern found, falling back to ZIP search")
        for btn in soup.select('a.btn-zip'):
            if "ZIP" in btn.text:
                return "Single", btn['href']
        for btn in soup.select('a.btn'):
            href = btn.get('href', '')
            if 'linkz.mom' in href:
                return "Single", href
        return None

def get_quality_servers(linkz_url):
    log(f"Opening linkz.mom: {linkz_url}")
    res = safe_request(linkz_url)
    if not res:
        return []
    soup = BeautifulSoup(res.text, 'html.parser')
    container = soup.select_one('div.download-links-div')
    if not container:
        return []

    qualities = []
    h4_tags = container.find_all('h4')
    for h4 in h4_tags:
        quality = h4.get_text(strip=True)
        next_div = h4.find_next_sibling('div', class_='downloads-btns-div')
        servers = []
        if next_div:
            for a in next_div.find_all('a', class_='btn'):
                href = a.get('href', '')
                label = a.get_text(strip=True)
                servers.append((label, href))
        if servers:
            qualities.append((quality, servers))
    return qualities

def get_direct_download_link(gamerxyt_url):
    log(f"Visiting gamerxyt page: {gamerxyt_url}")
    res = safe_request(gamerxyt_url)
    if not res:
        return None
    soup = BeautifulSoup(res.text, 'html.parser')
    primary = soup.select_one('a.btn-danger[href*="technorozen"]')
    if primary and "Download [Server : 10Gbps]" in primary.text:
        return primary['href']
    fallback = soup.select_one('a.btn-success[href*="pixeldrain"]')
    if fallback and "Download [PixelServer" in fallback.text:
        return fallback['href']
    return None

def get_hubcloud_final_link(hub_url):
    log(f"Fetching HubCloud page: {hub_url}")
    res = safe_request(hub_url)
    if not res:
        return None
    soup = BeautifulSoup(res.text, 'html.parser')
    gen_link_tag = soup.select_one('a.btn-primary[href*="gamerxyt.com"]')
    if not gen_link_tag:
        return None
    return get_direct_download_link(gen_link_tag['href'])

def get_vcloud_final_link(vcloud_url):
    log(f"Fetching VCloud page: {vcloud_url}")
    res = safe_request(vcloud_url)
    if not res:
        return None
    soup = BeautifulSoup(res.text, 'html.parser')
    script_tag = soup.find('script', string=re.compile('var url ='))
    if not script_tag:
        return None
    match = re.search(r"var url = '(https?://[^']+)'", script_tag.string)
    if not match:
        return None
    next_url = match.group(1)
    res = safe_request(next_url)
    if not res:
        return None
    soup = BeautifulSoup(res.text, 'html.parser')
    btn = soup.find('a', class_='btn btn-danger btn-lg h6', href=re.compile('https://gpdl3.technorozen'))
    if btn:
        final_page = safe_request(btn['href'])
        if not final_page:
            return None
        final_soup = BeautifulSoup(final_page.text, 'html.parser')
        final_link = final_soup.find('a', id='vd')
        if final_link:
            return final_link['href']
    pixel = soup.find('a', class_='btn btn-success btn-lg h6', href=re.compile('pixeldrain'))
    if pixel:
        return pixel['href']
    return None
