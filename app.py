#!/usr/bin/env python

import os, sys, argparse, logging, json, time
import requests

def backfill():
    # First, we get the latest round
    latest = get_latest_round()

    # Now, we get the range of all rounds from 0
    ranges = range(1, latest)
    for i in ranges:
        log.info("Processing round: {}".format(i))
        
        # Download the round
        d = get_round(i)
        
        # Publish it, but only for a non-error state
        if d != None:
            if args.cf:
                sendto_cf(d)
            
            # Update the pointer
            l = d['round']
        else:
            log.info("Error downloading round {}. Attempting again in {} seconds".format(r, args.delay))
        
        # And wait for the next round
        time.sleep(int(args.delay))

def get_round(i):
    try:
        r = requests.get('https://{}/public/{}'.format(args.drand, i), timeout=2)
        
        if r.status_code == 200:
            r = r.json()
            if r['round'] == i:
                return r
            else:
                log.debug("{} did not match the expected output, this round may not exist".format(i))
                return None
        else:
            return None
    except requests.exceptions.ReadTimeout:
        return None

def get_latest_round():
    try:
        r = requests.get('https://{}/public/latest'.format(args.drand), timeout=2).json()
        return r['round']
    except:
        return None

def sendto_cf(d):
    try:
        r = requests.put(
            "https://api.cloudflare.com/client/v4/accounts/{}/storage/kv/namespaces/{}/values/{}".format(
                args.cf_account,
                args.cf_namespace,
                "{}.{}".format(args.drand.replace(".", ""), d['round'])
            ),
            headers={
                'Authorization': "Bearer {}".format(args.cf_token)
            },
            data=json.dumps(d)
        )
    except:
        return None

if __name__ == '__main__':

    parser = argparse.ArgumentParser()

    # drand server
    parser.add_argument("-d", "--drand", help="drand server to archive", default=os.getenv("DRAND_SERVER", "drand.cloudflare.com"))

    # modes
    parser.add_argument("-b", "--backfill", help="backfill workers KV with the results of all rounds", action="store_true")
    parser.add_argument("-sv", "--server", help="run a server to update the archive as live", action="store_true")

    # config
    parser.add_argument("-dl", "--delay", help="pause between each check", default=os.getenv("DELAY", "5"))

    # storage
    ## cloudflare (workers kv)
    parser.add_argument("--cf", help="store data using Cloudflare Workers KV", action="store_true")
    parser.add_argument("--cf-account", help="cloudflare account id", default=os.getenv("CLOUDFLARE_ACCOUNT", ""))
    parser.add_argument("--cf-token", help="cloudflare api token", default=os.getenv("CLOUDFLARE_TOKEN", ""))
    parser.add_argument("--cf-namespace", help="cloudflare kv namespace", default=os.getenv("CLOUDFLARE_NAMESPACE", ""))

    ## s3

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

                # Publish it, but only for a non-error state
                if d != None:
                    if args.cf:
                        sendto_cf(d)
                    
                    # Update the pointer
                    l = d['round']
                else:
                    log.info("Error downloading round {}. Attempting again in {} seconds".format(r, args.delay))
            else:
                log.info("Round has not proceeded yet, still at round {}".format(r))

            # And wait for the next round
            time.sleep(int(args.delay))
