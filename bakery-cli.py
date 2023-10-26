#!/usr/bin/python

import bakery
from time import sleep

if __name__ == "__main__":
    sleep(0.5)
    if not bakery.dryrun:
        raise OSError("Protection against dum!")
    bakery.populate_messages()
    res = bakery.install()
    sleep(0.5)
    print("Exited with exit code:", res)
