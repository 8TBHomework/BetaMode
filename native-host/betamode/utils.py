import requests


def download(url, path):
    r = requests.get(url)
    with open(path, "wb") as f:
        f.write(r.content)
