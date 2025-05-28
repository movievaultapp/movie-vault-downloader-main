from flask import Flask, render_template, request, redirect, url_for
from scraper import get_search_results, get_linkz_url, get_quality_servers, get_hubcloud_final_link, get_vcloud_final_link

app = Flask(__name__)

# Temporary session-like store (use real session or DB for production)
cache = {}

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/search')
def search():
    query = request.args.get("query")
    if not query:
        return redirect(url_for('index'))

    results = get_search_results(query)
    if not results:
        return render_template("error.html", error_message="No results found.")

    cache['results'] = results
    return render_template("results.html", results=[{"title": r[0]} for r in results])

@app.route('/details', methods=["POST"])
def details():
    idx = int(request.form.get("index"))
    if 'results' not in cache:
        return redirect(url_for("index"))

    selected_title, selected_url = cache['results'][idx]
    result = get_linkz_url(selected_url)

    if isinstance(result, dict):
        # Multiple seasons
        cache['seasons'] = result
        cache['title'] = selected_title
        return render_template("seasons.html", title=selected_title, seasons=list(result.keys()))
    elif isinstance(result, tuple):
        season, linkz_url = result
        cache['linkz_url'] = linkz_url
        qualities = get_quality_servers(linkz_url)
        if not qualities:
            return render_template("error.html", error_message="No quality options found.")
        cache['qualities'] = qualities
        cache['title'] = selected_title
        return render_template("qualities.html", title=selected_title, qualities=qualities)
    else:
        return render_template("error.html", error_message="No download links found.")

@app.route('/select_season', methods=["POST"])
def select_season():
    season = request.form.get("season")
    if 'seasons' not in cache or season not in cache['seasons']:
        return redirect(url_for("index"))

    linkz_url = cache['seasons'][season]
    cache['linkz_url'] = linkz_url
    qualities = get_quality_servers(linkz_url)
    if not qualities:
        return render_template("error.html", error_message="No quality options found.")
    cache['qualities'] = qualities
    return render_template("qualities.html", title=cache.get("title", "Select Quality"), qualities=qualities)

@app.route('/download', methods=["POST"])
def download():
    q_index = int(request.form.get("quality"))
    qualities = cache.get("qualities")
    if not qualities:
        return redirect(url_for("index"))

    selected_quality, servers = qualities[q_index]
    working_links = []
    leftover_qualities = []

    for name, link in servers:
        if "hubcloud" in link.lower():
            final_link = get_hubcloud_final_link(link)
            if final_link:
                working_links.append(final_link)
                break
        elif "vcloud" in link.lower():
            final_link = get_vcloud_final_link(link)
            if final_link:
                working_links.append(final_link)
                break
        else:
            leftover_qualities.append((name, link))

    if not working_links and leftover_qualities:
        # fallback to manual options
        return render_template("download.html", title=f"Links for {selected_quality}", working_links=[], leftover_qualities=leftover_qualities)

    return render_template("download.html", title=f"Download - {selected_quality}", working_links=working_links, leftover_qualities=leftover_qualities)

@app.errorhandler(500)
def server_error(e):
    return render_template("error.html", error_message="An unexpected error occurred."), 500

if __name__ == '__main__':
    app.run(debug=True)
