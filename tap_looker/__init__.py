#!/usr/bin/env python3

import sys
import json
import argparse
import singer
from singer import metadata, utils
from tap_looker.client import LookerClient, API_VERSION_DEFAULT
from tap_looker.discover import discover
from tap_looker.sync import sync

LOGGER = singer.get_logger()

REQUIRED_CONFIG_KEYS = [
    'subdomain',
    'client_id',
    'client_secret',
    'start_date',
    'user_agent'
]

def do_discover():

    LOGGER.info('Starting discover')
    catalog = discover()
    json.dump(catalog.to_dict(), sys.stdout, indent=2)
    LOGGER.info('Finished discover')


@singer.utils.handle_top_exception(LOGGER)
def main():

    parsed_args = singer.utils.parse_args(REQUIRED_CONFIG_KEYS)

    with LookerClient(subdomain=parsed_args.config['subdomain'],
                      client_id=parsed_args.config['client_id'],
                      client_secret=parsed_args.config['client_secret'],
                      domain=parsed_args.config['domain'],
                      api_port=parsed_args.config['api_port'],
                      api_version=API_VERSION_DEFAULT,
                      user_agent=parsed_args.config['user_agent']) as client:

        state = {}
        if parsed_args.state:
            state = parsed_args.state

        if parsed_args.discover:
            do_discover()
        elif parsed_args.catalog:
            sync(client=client,
                 config=parsed_args.config,
                 catalog=parsed_args.catalog,
                 state=state)

if __name__ == '__main__':
    main()
