#!/usr/bin/env python3
import mimetypes
import os
from tempfile import TemporaryDirectory
from threading import Thread, Semaphore

import requests
from PIL import Image
from datauri import DataURI, InvalidDataURI
from nudenet import NudeDetector

from betamode import DEFAULT_CENSORED_LABELS
from betamode.ipc import get_message, send_message
from betamode.util import filter_tuples


class BetaMode:
    def __init__(self, tempdir):
        self.tempdir = tempdir
        self.detector = NudeDetector("default")
        self.fetch_queue = []
        self.fetch_semaphore = Semaphore()
        self.censor_queue = []
        self.censor_semaphore = Semaphore()
        self.failed_jobs = []
        self.session = requests.session()

    def enqueue_fetch(self, img_id, img_url):
        if img_id and img_url:
            self.fetch_queue.append((img_id, img_url))
            self.fetch_semaphore.release()

    def enqueue_censor(self, img_id, data_bytes, mime_type):
        if img_id and data_bytes and mime_type:
            self.censor_queue.append((img_id, data_bytes, mime_type))
            self.censor_semaphore.release()

    def dequeue_fetch(self, img_id):
        self.fetch_queue = filter_tuples(self.fetch_queue, 0, img_id)

    def dequeue_censor(self, img_id):
        self.censor_queue = filter_tuples(self.censor_queue, 0, img_id)

    def work_fetch(self):
        while True:
            self.fetch_semaphore.acquire()
            for img_id, img_url in self.fetch_queue:
                self.dequeue_fetch(img_id)
                try:
                    data_bytes, mime_type = self.fetch(img_url)
                    self.enqueue_censor(img_id, data_bytes, mime_type)
                except Exception as e:
                    self.failed_jobs.append((img_id, "fetch", str(e)))

    def work_censor(self):
        while True:
            self.censor_semaphore.acquire()
            for img_id, data_bytes, mime_type in self.censor_queue:
                self.dequeue_censor(img_id)
                try:
                    data = self.censor(img_id, data_bytes, mime_type)
                    response = {
                        "type": "result",
                        "id": img_id,
                        "data": data
                    }
                    send_message(response)
                except Exception as e:
                    self.failed_jobs.append((img_id, "censor", str(e)))

    def fetch(self, img_url) -> (bytes, str):
        try:  # if img_url is a data uri, just extract our information
            data_uri = DataURI(img_url)
            data_bytes = data_uri.data
            mime_type = data_uri.mimetype
        except InvalidDataURI:  # otherwise its probably an URL
            r = self.session.get(img_url)
            data_bytes = r.content
            mime_type = r.headers.get("Content-Type")
        return data_bytes, mime_type

    def censor(self, img_id, data_bytes, mime_type) -> str:
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

        fetch_thread = Thread(target=bm.work_fetch)
        fetch_thread.start()
        censor_thread = Thread(target=bm.work_censor)
        censor_thread.start()

        while True:
            message = get_message()

            if message["type"] == 0:  # enqueue new image
                bm.enqueue_fetch(message["id"], message["url"])

            elif message["type"] == 1:  # dequeue image
                bm.dequeue_fetch(message["id"])
                bm.dequeue_censor(message["id"])

            elif message["type"] == 2:  # query status
                send_message({
                    "type": "status",
                    "fetch": {
                        "queue": len(bm.fetch_queue),
                        "alive": fetch_thread.is_alive(),
                    },
                    "censor": {
                        "queue": len(bm.censor_queue),
                        "alive": censor_thread.is_alive()
                    },
                    "failed": bm.failed_jobs
                })

            elif message["type"] == 3:  # settings
                if "user_agent" in message:
                    bm.session.headers.update({'User-Agent': message["user_agent"]})


if __name__ == '__main__':
    main()
