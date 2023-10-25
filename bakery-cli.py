#!/usr/bin/python

import bakery
from time import sleep

if __name__ == "__main__":
    sleep(1)
    bakery.populate_messages()
    res = bakery.install()
    print(bakery.messages)
    print("Result:", res)
