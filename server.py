from flask import Flask, request, send_file, redirect, url_for
from datetime import datetime
from os import path, listdir

from markdown_to_html import MarkdownToHtmlConverter

POSTS_DIR = {
    "private": "../../Dropbox/journal",
    "public": "../../Dropbox/Apps/journal-public/notes",
}
MEDIA_DIR = "media"
MONTHS = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]

app = Flask(__name__)


@app.route("/")
def index():
    blog_id = request.args.get('blog_id')
    if not blog_id:
        return "Missing blog_id parameter", 400
    
    posts_dir = POSTS_DIR[blog_id]
    paths = listdir(posts_dir)
    paths = [path for path in paths if path.endswith(".txt")]
    paths = [tuple(path.replace(".txt", "").split(" ")) for path in paths]
    years = reversed(sorted(list({path[1] for path in paths})))

    posts = []
    for year in years:
        months = []
        for month in MONTHS:
            if (month, year) in paths:
                months.append(month)

        posts.append((year, months))

    content = "<div id='dates'>\n"
    for year, months in posts:
        content += f"<h4>{year}</h4>\n"
        paths = [f'<li><a href="p/{year}/{month}?blog_id={blog_id}">{month}</a></li>' for month in months]
        content += "<ul>\n" + "\n".join(paths) + "</ul>"

    return """
<!DOCTYPE html>
<html>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Urnal</title>
<link rel="stylesheet" href="/media/style.css" />
<body>
""" + content + """
<a href="/new"><div id="newPostFloatingLink">[+]</div></a>
</body>
</html>
"""


@app.route("/p/<year>/<month>")
def list_for_month(year, month):
    blog_id = request.args.get('blog_id')
    if not blog_id:
        return "Missing blog_id parameter", 400
    
    convert_markdown = request.args.get('convert_markdown', 'true').lower() == 'true'
    
    posts = get_posts(f"{month} {year}.txt", blog_id)
    if not posts:
        return "No posts found for this month!"

    posts = [MarkdownToHtmlConverter().convert(post) if convert_markdown else post for post in posts]

    posts = [f"<article>{post}</article>" for post in posts]
    posts = "\n\n".join(posts)

    return """
<!DOCTYPE html>
<html>
<title>Urnal</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="/media/style.css" />
<body>
<nav>
  Nav: <a href="/?blog_id=private">[home private]</a> | <a href="/?blog_id=public">[home PUBLIC]</a>
</nav>
<div id="posts">
""" + posts + """
</div>
<a href="/new"><div id="newPostFloatingLink">[+]</div></a>
<a id="footer">&nbsp;</a>
</body>
</html>
"""


@app.route("/media/<path:file_path>")
def media(file_path):
    return send_file(path.join(MEDIA_DIR, file_path))


@app.route("/new", methods=["GET"])
def editor():
    return send_file("editor.html")


@app.route("/new", methods=["POST"])
def create():
    blog_id = request.form.get('blog_id')
    post_body = request.form.get('post_body')
    
    if not blog_id or not post_body:
        return "Missing required form fields", 400
    
    t = datetime.now()
    post_file = t.strftime("%B %Y.txt")
    post_time = t.strftime("%a %b %d %H:%M:%S %Y")
    post_url = t.strftime("/p/%Y/%B")

    post_body = post_time + "\n\n" + post_body

    posts_dir = POSTS_DIR[blog_id]
    file_path = posts_dir + "/" + post_file
    mode = "w"

    if path.exists(file_path):
        mode = "a"
        post_body = "\n\n--\n" + post_body

    with open(file_path, mode) as f:
        f.write(post_body)

    return redirect(post_url + f"?blog_id={blog_id}#footer")


def get_posts(file, blog_id: str):
    posts_dir = POSTS_DIR[blog_id]
    file_path = posts_dir + "/" + file
    if not path.exists(file_path):
        return

    posts = ""
    with open(file_path) as f:
        posts = f.read()

    posts = posts.split("\n--\n")

    return posts


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=9876, debug=True)
