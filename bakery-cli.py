#!/usr/bin/python

import bakery
from time import sleep

if __name__ == "__main__":
    sleep(0.5)
    bakery.populate_messages()
    langs, models = bakery.kb_supported()
    # res = bakery.install()
    sleep(0.5)
    print(bakery.messages)
    # print("Exited with exit code:", res)
