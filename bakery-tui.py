#!/usr/bin/python

import bakery
from time import sleep

if __name__ == "__main__":
    sleep(0.5)
    if not bakery.dryrun:
        raise OSError("Protection against dum!")
    # res = bakery.install()
    bakery.lrun(["ls", "-l"], force=True, silent=True)
    # print("Exited with exit code:", res)
