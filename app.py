#!/usr/bin/env python

import os, sys, argparse, logging, json, time
import requests

def backfill():
    # First, we get the latest round
    latest = get_latest_round()

    # Now, we get the range of all rounds from 0
    ranges = range(0, latest)
    for i in ranges:
        log.debug("Processing round: {}".format(i))
        get_round(i)


def get_round(i):
    try:
        r = requests.get('https://{}/public/{}'.format(args.drand, i), timeout=2).json()
        
        if r['round'] == i:
            return r
        else:
            log.debug("{} did not match the expected output, this round may not exist".format(i))
            return None
    except requests.exceptions.ReadTimeout:
        return None

def get_latest_round():
    try:
        r = requests.get('https://{}/public/latest'.format(args.drand), timeout=2).json()
        return r['round']
    except:
        return None

if __name__ == '__main__':

    parser = argparse.ArgumentParser()

    # drand server
    parser.add_argument("-d", "--drand", help="drand server to archive", default="drand.cloudflare.com")

    # modes
    parser.add_argument("-b", "--backfill", help="backfill workers KV with the results of all rounds", action="store_true")
    parser.add_argument("-sv", "--server", help="run a server to update the archive as live", action="store_true")

    # Verbose mode
    parser.add_argument("--verbose", "-v", help="increase output verbosity", action="store_true")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    log = logging.getLogger(__name__)

    if args.backfill:
        backfill()
        exit()
    
    if args.server:
        l = get_latest_round()

        while True:
            # Grab the latest round
            r = get_latest_round()

            if r > l:
                # We have a new round
                log.info("Downloading next round: {}".format(r))

                # Download it
                d = get_round(r)

                # Publish it

                # Update the pointer
                l = d['round']
            else:
                log.info("Round has not proceeded yet, still at round {}".format(r))

            # And wait for the next round
            time.sleep(3)
