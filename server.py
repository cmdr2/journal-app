from fastapi import FastAPI, Form, status
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse

from datetime import datetime
from os import path, listdir

POSTS_DIR = "../../Dropbox/journal"
MEDIA_DIR = "media"
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

app = FastAPI()

@app.get("/")
def index():
    paths = listdir(POSTS_DIR)
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
        paths = [f'<li><a href="p/{year}/{month}">{month}</a></li>' for month in months]
        content += "<ul>\n" + "\n".join(paths) + "</ul>"

    return HTMLResponse("""
<!DOCTYPE html>
<html>
<title>Urnal</title>
<link rel="stylesheet" href="/media/style.css" />
<body>
""" + content + """
<a href="/new"><div id="newPostFloatingLink">[+]</div></a>
</body>
</html>
""")

@app.get("/p/{year}/{month}")
def list_for_month(year, month):
    posts = get_posts(f"{month} {year}.txt")
    if not posts:
        return "No posts found for this month!"

    posts = [f"<article>{post}</article>" for post in posts]
    posts = "\n\n".join(posts)

    return HTMLResponse("""
<!DOCTYPE html>
<html>
<title>Urnal</title>
<link rel="stylesheet" href="/media/style.css" />
<body>
<nav>
  Nav: <a href="/">[home]</a>
</nav>
<div id="posts">
""" + posts + """
</div>
<a href="/new"><div id="newPostFloatingLink">[+]</div></a>
<a id="footer">&nbsp;</a>
</body>
</html>
""")

@app.get("/media/{file_path}")
def media(file_path):
    return FileResponse(path.join(MEDIA_DIR, file_path))

@app.get("/new")
def editor():
    return HTMLResponse("""
<!DOCTYPE html>
<html>
<title>Urnal</title>
<link rel="stylesheet" href="/media/style.css" />
<body>
<nav>
  Nav: <a href="/">[home]</a>
</nav>
<form method="post" action="/new">
    <textarea id="editor" name="post_body" autofocus></textarea>
    <br/>
    <button id="createPostBtn" type="submit">Post</button>
</form>
</body>
</html>
""")

@app.post("/new")
async def create(post_body: str = Form(None)):
    t = datetime.now()
    post_file = t.strftime("%B %Y.txt")
    post_time = t.strftime("%a %b %d %H:%M:%S %Y")
    post_url = t.strftime("/p/%Y/%B")

    post_body = post_time + "\n\n" + post_body

    file_path = POSTS_DIR + "/" + post_file
    mode = "w"

    if path.exists(file_path):
        mode = "a"
        post_body = "\n\n--\n" + post_body

    with open(file_path, mode) as f:
        f.write(post_body)

    return RedirectResponse(url=post_url + "#footer", status_code=status.HTTP_303_SEE_OTHER)

def get_posts(file):
    file_path = POSTS_DIR + "/" + file
    if not path.exists(file_path):
        return

    posts = ""
    with open(file_path) as f:
        posts = f.read()

    posts = posts.split("\n--\n")

    return posts
