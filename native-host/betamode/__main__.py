#!/usr/bin/env python3
import mimetypes
import os
from queue import Queue
from tempfile import TemporaryDirectory
from threading import Thread, Semaphore

import requests
from PIL import Image
from datauri import DataURI, InvalidDataURI
from nudenet import NudeDetector

from betamode import DEFAULT_CENSORED_LABELS
from betamode.ipc import get_message, send_message


class BetaMode:
    def __init__(self, tempdir):
        self.tempdir = tempdir
        self.detector = NudeDetector("default")
        self.queue = Queue()
        self.url_map = {}

    def enqueue(self, img_id, img_url):
        if img_id not in self.url_map and img_id is not None and img_url is not None:
            self.url_map[img_id] = img_url
            self.queue.put(img_id)

    def dequeue(self, img_id):
        if img_id in self.url_map:
            # Don't need to touch queue, as it will be handled by worker
            return self.url_map.pop(img_id)
        return None

    def work(self):
        while True:
            img_id = self.queue.get()
            img_url = self.dequeue(img_id)
            if img_url:
                try:
                    data = self.censor(img_id, img_url)
                except:
                    data = None
                response = {
                    "type": "result",
                    "id": img_id,
                    "data": data
                }
                send_message(response)

    def censor(self, img_id, img_url) -> str:
        try:  # if img_url is a data uri, just extract our information
            data_uri = DataURI(img_url)
            data_bytes = data_uri.data
            mime_type = data_uri.mimetype
        except InvalidDataURI:  # otherwise its probably an URL
            r = requests.get(img_url)
            data_bytes = r.content
            mime_type = r.headers.get("Content-Type")

        extension = mimetypes.guess_extension(mime_type)
        if extension is None:
            extension = ".dat"
        filename = f"{img_id}{extension}"
        in_path = os.path.join(self.tempdir, filename)
        censored_path = os.path.join(self.tempdir, f"c_{filename}")
        resized_path = os.path.join(self.tempdir, f"cr_{img_id}.webp")

        if not os.path.isfile(resized_path):
            with open(in_path, "wb") as f:
                f.write(data_bytes)

            self.detector.censor(in_path, censored_path, parts_to_blur=DEFAULT_CENSORED_LABELS)

            # Reduce size to get below 1MB TODO: make this more reliable
            with Image.open(censored_path) as im:
                im.thumbnail((2000, 1000))
                im.save(resized_path, "WEBP", quality=60)

        return DataURI.from_file(resized_path)


def main():
    with TemporaryDirectory(prefix="betamode") as tempdir:
        bm = BetaMode(tempdir)
        input_thread = Thread(target=bm.work)
        input_thread.start()

        while True:
            message = get_message()

            if message["type"] == 0:  # enqueue new image
                bm.enqueue(message["id"], message["url"])

            elif message["type"] == 1:  # dequeue image
                bm.dequeue(message["id"])

            elif message["type"] == 2:  # query status
                send_message({
                    "type": "status",
                    "queue": bm.queue.qsize(),
                    "worker": input_thread.is_alive()
                })


if __name__ == '__main__':
    main()
