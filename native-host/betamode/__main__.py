#!/usr/bin/env python3
import os
from tempfile import TemporaryDirectory
from threading import Thread, Semaphore

import cv2
import numpy as np
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

    def enqueue_censor(self, img_id, data_bytes):
        if img_id:
            self.censor_queue.append((img_id, data_bytes))
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
                    cache_path = self.generate_cache_path(img_id)

                    data_bytes = None
                    if not os.path.isfile(cache_path):  # if file is already cached skip fetch
                        data_bytes = self.fetch(img_url)

                    self.enqueue_censor(img_id, data_bytes)
                except Exception as e:
                    self.failed_jobs.append((img_id, "fetch", str(e)))

    def work_censor(self):
        while True:
            self.censor_semaphore.acquire()
            for img_id, data_bytes in self.censor_queue:
                self.dequeue_censor(img_id)
                try:
                    cache_path = self.generate_cache_path(img_id)

                    if not os.path.isfile(cache_path):
                        image = self.censor_custom(data_bytes, parts_to_blur=DEFAULT_CENSORED_LABELS)

                        # Reduce size to get below 1MB TODO: make this more reliable
                        image.thumbnail((2000, 1000))
                        image.save(cache_path, "WEBP", quality=60)

                    response = {
                        "type": "result",
                        "id": img_id,
                        "data": DataURI.from_file(cache_path)
                    }
                    send_message(response)
                except Exception as e:
                    self.failed_jobs.append((img_id, "censor", str(e)))

    def fetch(self, img_url) -> bytes:
        try:  # if img_url is a data uri, just extract our information
            data_uri = DataURI(img_url)
            data_bytes = data_uri.data
        except InvalidDataURI:  # otherwise its probably an URL
            r = self.session.get(img_url)
            data_bytes = r.content
        return data_bytes

    def censor_custom(self, data_bytes, parts_to_blur):
        img_buff = np.frombuffer(data_bytes, np.uint8)
        image = cv2.imdecode(img_buff, cv2.IMREAD_UNCHANGED)
        boxes = self.detector.detect(image)

        boxes = [i["box"] for i in boxes if i["label"] in parts_to_blur]

        for box in boxes:
            part = image[box[1]: box[3], box[0]: box[2]]
            image = cv2.rectangle(
                image, (box[0], box[1]), (box[2], box[3]), (0, 0, 0), cv2.FILLED
            )

        color_coverted = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        return Image.fromarray(color_coverted)

    def generate_cache_path(self, img_id):
        return os.path.join(self.tempdir, f"{img_id}.webp")


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
