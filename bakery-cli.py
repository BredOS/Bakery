#!/usr/bin/python

import bakery
from time import sleep

if __name__ == "__main__":
    bakery.ensure_localdb()
    print(bakery.messages)
