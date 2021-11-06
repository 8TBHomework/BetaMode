#!/usr/bin/env python3
import os
from base64 import urlsafe_b64decode
from hashlib import sha1
from tempfile import mkdtemp
from urllib.parse import urlparse

import cv2
import numpy as np
import requests
from PIL import Image
from datauri import DataURI, InvalidDataURI
from fastapi import FastAPI, Request
from nudenet import NudeDetector
from starlette.datastructures import Headers
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse, PlainTextResponse

DEFAULT_CENSORED_LABELS = [
    "EXPOSED_GENITALIA_F",
    "COVERED_GENITALIA_F",
    "EXPOSED_BREAST_F",
    "EXPOSED_ANUS"
]

ALLOWED_SCHEMES = [
    "http",
    "https",
    "data"
]


def filter_headers(headers, fields):
    return list(filter(lambda x: x[0].lower() not in fields, headers))


class BetaMode:
    def __init__(self, tempdir):
        self.tempdir = tempdir
        self.detector = NudeDetector("default")
        self.session = requests.session()

    def fetch(self, img_url, headers: Headers) -> bytes:
        try:  # if img_url is a data uri, just extract the information
            data_uri = DataURI(img_url)
            data_bytes = data_uri.data
        except InvalidDataURI:  # otherwise its probably an URL
            cleaned_headers = filter_headers(headers.items(), ["host"])
            r = self.session.get(img_url, headers=dict(cleaned_headers))
            data_bytes = r.content
        return data_bytes

    def censor_custom(self, data_bytes, parts_to_blur):
        img_buff = np.frombuffer(data_bytes, np.uint8)
        image = cv2.imdecode(img_buff, cv2.IMREAD_UNCHANGED)
        boxes = self.detector.detect(image)

        boxes = [i["box"] for i in boxes if i["label"] in parts_to_blur]

        for box in boxes:
            image = cv2.rectangle(
                image, (box[0], box[1]), (box[2], box[3]), (0, 0, 0), cv2.FILLED
            )

        color_converted = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        return Image.fromarray(color_converted)

    def generate_cache_path(self, img_id):
        return os.path.join(self.tempdir, f"{img_id}.webp")


app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_headers=["*"])
bm = BetaMode(mkdtemp(prefix="betamode"))


@app.get("/censored/{url_b64}")
def censor(url_b64: str, request: Request):
    img_url = urlsafe_b64decode(url_b64 + '=' * (4 - len(url_b64) % 4)).decode()
    img_url_parsed = urlparse(img_url)

    if img_url_parsed.scheme not in ALLOWED_SCHEMES:
        return PlainTextResponse(f"scheme {img_url_parsed.scheme} not allowed", 400)

    img_id = sha1(img_url.encode()).hexdigest()

    cache_path = bm.generate_cache_path(img_id)
    if not os.path.isfile(cache_path):  # if file is already cached skip fetch
        data_bytes = bm.fetch(img_url, request.headers)

        image = bm.censor_custom(data_bytes, parts_to_blur=DEFAULT_CENSORED_LABELS)

        image.save(cache_path, "WEBP", quality=60)

    return FileResponse(cache_path)
