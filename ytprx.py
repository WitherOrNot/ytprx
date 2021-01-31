from flask import Flask, request, Response
from urllib.parse import quote
from html import escape
from youtube_dl import YoutubeDL
import requests
import json

app = Flask(__name__)

def stream_resp(response):
    with response as stream:
        for chunk in stream.iter_content(chunk_size=8192):
            yield chunk

def serve_proxy(to_url, filename):
    status = 302

    while status == 302:
        resp = requests.get(
            url=to_url,
            headers=dict(filter(lambda h: h[0].lower() != "host", request.headers)),
            allow_redirects=False,
            stream=True
        )

        status = resp.status_code
    
    headers = dict(filter(lambda h: h[0].lower() not in ["content-disposition", "location"], resp.raw.headers.items()))
    headers["Content-Disposition"] = "inline; filename*=UTF-8''" + quote(filename, safe="")

    return Response(stream_resp(resp), resp.status_code, headers)

def search(query):
    data = requests.get("https://www.youtube.com/results", params={"search_query": query}).text
    start = data.find("ytInitialData = {") + 16
    end = start + 15 + data[start+16:].find("</script>")
    j = json.loads(data[start:end])
    videos = list(filter(lambda i: "videoRenderer" in i, j["contents"]["twoColumnSearchResultsRenderer"]["primaryContents"]["sectionListRenderer"]["contents"][0]["itemSectionRenderer"]["contents"]))
    results = list(map(lambda i: (i["videoRenderer"]["videoId"], i["videoRenderer"]["title"]["runs"][0]["text"]), videos))
    return results

@app.route("/")
def index():
    return '<html><title>sicko mode the website</title><form action="/search">Search for video:<br><input type="text" name="query" autocomplete="off"><br><br><br><input type="submit" value="Search"></form></html>'

@app.route("/search")
def results():
    query = request.args["query"]

    resp = "<title>sicko mode the website</title><h1>Search results for &quot;" + escape(query) + "&quot;</h1><hr>"
    for vid, title in search(query):
        resp += '<a href="/watch?v='+vid+'">'+ escape(title) +'</a><br />'
    
    return resp

@app.route("/video")
def video():
    vid = request.args["v"]

    with YoutubeDL({"quiet": True}) as ytdl:
        info = ytdl.extract_info(vid, download=False)
    
    streams = dict(map(lambda i: (i["format_id"], i["url"]), info["formats"]))
    stream_url = streams.get("22", streams["18"])
    return serve_proxy(stream_url, info["title"] + "_" + vid + ".mp4")

@app.route("/watch")
def watch():
    vid = request.args["v"]
    return '<title>sicko mode the website</title><video controls autoplay width="1280" height="720" src="/video?v=' + escape(vid) + '"></video>'

if __name__ == "__main__":
    app.run(host="0.0.0.0")
