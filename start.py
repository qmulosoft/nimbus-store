#!/usr/bin/env python3.6

import argparse
import os
import sqlite3
from src.nimbus_store import API
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

parser.add_argument(
    "-m", "--migrate",
    help="migrate the database (up)",
    action="store_true"
)

args = parser.parse_args()

sql_conn = sqlite3.connect(args.db)

if args.migrate:
    import migrate as migrate
    migration = migrate.Migration(os.path.dirname(os.path.realpath(__file__)) + "/db/sqlite/migrations", sql_conn)
    migration()

app = API(sql_conn, args.volume)

httpd = simple_server.make_server("0.0.0.0", 4242, app)
httpd.serve_forever()
