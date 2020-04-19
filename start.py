#!/usr/bin/env python3.6

import argparse
import sqlite3
from lib.api import API
from wsgiref import simple_server

parser = argparse.ArgumentParser(
    description="Nimbus distributed data store service"
)

parser.add_argument(
    'volume',
    help="the local system path to use as a nimbus storage root"
)

parser.add_argument(
    'db',
    help="the path to the local instance of the database file"
)

args = parser.parse_args()

sql_conn = sqlite3.connect(args.db)

app = API(sql_conn, args.volume)

httpd = simple_server.make_server("localhost", 4242, app)
httpd.serve_forever()
