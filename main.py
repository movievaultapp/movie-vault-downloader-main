from flask import Flask, render_template, request, redirect, url_for
from scraper import get_search_results, get_linkz_url, get_quality_servers, get_hubcloud_final_link, get_vcloud_final_link

app = Flask(__name__)
cache = {}

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/search')
def search():
    query = request.args.get("query")
    if not query:
        return redirect(url_for('index'))

    print(f"[LOG] Searching for: {query}")
    results = get_search_results(query)
    print(f"[LOG] Found {len(results)} results.")

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
    print(f"[LOG] Selected: {selected_title}")
    result = get_linkz_url(selected_url)

    if isinstance(result, dict):  # Multiple seasons
        print(f"[LOG] Detected multiple seasons")
        cache['seasons'] = result
        cache['title'] = selected_title
        return render_template("seasons.html", title=selected_title, seasons=list(result.keys()))

    elif isinstance(result, tuple):  # Single season or movie
        season, linkz_url = result
        print(f"[LOG] Season {season} → {linkz_url}")
        cache['linkz_url'] = linkz_url
        cache['title'] = selected_title
        qualities = get_quality_servers(linkz_url)
        print(f"[LOG] Found qualities: {qualities}")

        if not qualities:
            return render_template("error.html", error_message="No qualities found.")
        cache['qualities'] = qualities
        return render_template("qualities.html", title=selected_title, qualities=qualities)

    return render_template("error.html", error_message="Could not extract download links.")

@app.route('/select_season', methods=["POST"])
def select_season():
    season = request.form.get("season")
    if not season or 'seasons' not in cache:
        return redirect(url_for("index"))

    linkz_url = cache['seasons'][season]
    print(f"[LOG] Season selected: {season} → {linkz_url}")
    cache['linkz_url'] = linkz_url
    qualities = get_quality_servers(linkz_url)
    print(f"[LOG] Found qualities: {qualities}")

    if not qualities:
        return render_template("error.html", error_message="No qualities found.")

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
    fallback_links = []

    for name, link in servers:
        print(f"[LOG] Trying server: {name} → {link}")
        if "hubcloud" in link.lower():
            final = get_hubcloud_final_link(link)
            if final:
                print(f"[LOG] ✅ Final HubCloud link: {final}")
                working_links.append(final)
                break
        elif "vcloud" in link.lower():
            final = get_vcloud_final_link(link)
            if final:
                print(f"[LOG] ✅ Final VCloud link: {final}")
                working_links.append(final)
                break
        else:
            fallback_links.append((name, link))

    return render_template("download.html",
                           title=f"Download - {selected_quality}",
                           working_links=working_links,
                           leftover_qualities=fallback_links)

@app.errorhandler(500)
def error_500(e):
    return render_template("error.html", error_message="An unexpected error occurred."), 500

if __name__ == '__main__':
    app.run(debug=True)
