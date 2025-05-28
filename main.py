
from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from scraper import (
    get_search_results,
    get_linkz_url,
    get_quality_servers,
    get_hubcloud_final_link,
    get_vcloud_final_link
)

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Required for session

CACHE = {
    "results": [],
    "selected": None,
    "linkz": None,
    "qualities": None,
}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/search')
def search():
    query = request.args.get('query')
    if not query:
        return redirect('/')

    results = get_search_results(query)
    CACHE["results"] = results

    if not results:
        error_message = "No results found for your search."
        return render_template('error.html', error_message=error_message)

    return render_template('results.html', results=[{"title": r[0]} for r in results])

@app.route('/details', methods=['POST'])
def details():
    idx = int(request.form.get('index'))
    title, url = CACHE["results"][idx]
    linkz = get_linkz_url(url)
    CACHE["selected"] = title
    CACHE["linkz"] = linkz
    
    if isinstance(linkz, dict):
        return render_template('seasons.html', 
                            title=title,
                            seasons=list(linkz.keys()))
    elif isinstance(linkz, tuple):
        season, link = linkz
        CACHE["qualities"] = get_quality_servers(link)
        return render_template('qualities.html', 
                            title=title,
                            qualities=CACHE["qualities"])

@app.route('/select_season', methods=['POST'])
def select_season():
    season = request.form.get('season')
    title = CACHE["selected"]
    link = CACHE["linkz"].get(season)
    CACHE["qualities"] = get_quality_servers(link)
    return render_template('qualities.html', 
                        title=title,
                        qualities=CACHE["qualities"])

@app.route('/download', methods=['POST'])
def download():
    quality_idx = int(request.form.get('quality'))
    servers = CACHE["qualities"][quality_idx][1]
    title = CACHE["selected"]
    
    working_links = []
    leftover_qualities = []
    
    for name, link in servers:
        if "hubcloud" in link.lower():
            final = get_hubcloud_final_link(link)
            if final:
                working_links.append(final)
        elif "vcloud" in link.lower():
            final = get_vcloud_final_link(link)
            if final:
                working_links.append(final)
        else:
            leftover_qualities.append((name, link))
    
    return render_template('download.html',
                        title=title,
                        working_links=working_links,
                        leftover_qualities=leftover_qualities)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
