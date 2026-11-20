import datetime
import os
import random
import time
import uuid
from datetime import datetime as dt
from pathlib import Path

import requests

counter = 0


def impure(order):
    # ruleid: python-clock
    order["at"] = time.time()
    # ruleid: python-clock
    order["day"] = dt.now()
    # ruleid: python-clock
    order["today"] = datetime.date.today()
    # ruleid: python-random
    order["roll"] = random.randint(1, 6)
    # ruleid: python-random
    order["id"] = uuid.uuid4()
    # ruleid: python-environment
    order["tz"] = os.environ["TZ"]
    # ruleid: python-environment
    order["home"] = os.getenv("HOME")
    # ruleid: python-file-io
    with open("audit.log", "a") as log:
        log.write("x")
    # ruleid: python-file-io
    order["text"] = Path("x").read_text()
    # ruleid: python-network-io
    order["remote"] = requests.get("https://example.invalid")
    # ruleid: python-console
    print(order)


def mutates_global():
    # ruleid: python-global-mutation
    global counter
    counter += 1


def counter_factory():
    count = 0

    def increment():
        # ruleid: python-global-mutation
        nonlocal count
        count += 1
        return count

    return increment


def pure(price: int, quantity: int, now: datetime.datetime) -> int:
    # ok: python-clock
    elapsed = now.timestamp()
    # ok: python-random
    choice = sorted([price, quantity])
    return price * quantity + int(elapsed) + choice[0]
