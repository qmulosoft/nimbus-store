#!/usr/bin/env python3

import sqlite3
import os
import argparse

" All this logic should, at some point, probably be abstracted and converted into a standalone lib"

_nimbus_migration_table = "__nimbus__mig_"

parser = argparse.ArgumentParser(
    description="Runs migrations to upgrade database state"
)

parser.add_argument(
    "action",
    choices=("up", "down"),
    help="whether to migrate or revert a migration"
)
parser.add_argument(
    "db",
    help="the sqlite database file to migrate",
)
parser.add_argument(
    "--dir",
    help="The directory containing the SQL migration files",
    default=os.path.dirname(__file__) + "/db/sqlite/migrations"
)

args = parser.parse_args()

sql_conn = sqlite3.connect(args.db)
# Get any migrations that have run before
cursor = sql_conn.cursor()
cursor.execute(
    f"CREATE TABLE IF NOT EXISTS {_nimbus_migration_table} (id INTEGER PRIMARY KEY AUTOINCREMENT, name VARCHAR, date DATETIME)")
# [(ID, name, date)]
migrations = cursor.execute(f"SELECT * FROM {_nimbus_migration_table}").fetchall()
ran_migrations = set(each[1] for each in migrations)


def run_migration(conn: sqlite3.Connection, filename: str, name: str, up=True) -> bool:
    cursor = conn.cursor()
    try:
        with open(filename) as f:
            if up:
                print(f"Running Migration {name}")
            else:
                print(f"Reverting Migration {name}")
            sql = f.read()
            cursor.executescript(sql)
            conn.commit()
            if up:
                cursor.execute(f"INSERT INTO {_nimbus_migration_table} (`name`, `date`) VALUES (?, datetime())", [name])
            else:
                cursor.execute(f"DELETE FROM {_nimbus_migration_table} WHERE `name` = ?", [name])
            conn.commit()
    except sqlite3.Error:
        conn.rollback()
        raise


mig_dir = args.dir
if not os.path.exists(mig_dir):
    print(f"migration directory {mig_dir} does not exist")
else:
    try:
        for _, _, files in os.walk(mig_dir):
            for file in files:
                if args.action == "up" and file.endswith(".up.sql"):
                    name = file[:-7]
                    if name not in ran_migrations:
                        run_migration(sql_conn, os.path.join(mig_dir, file), name)
                elif args.action == "down" and file.endswith('.dn.sql'):
                    name = file[:-7]
                    if name in ran_migrations:
                        run_migration(sql_conn, os.path.join(mig_dir, file), name, False)
    except sqlite3.Error as e:
        print(f"Error executing SQL for migration '{name}': {e}")
    except Exception as e:
        print(f"Unexpected error occurred opening migration directory or file: {e}")
    else:
        print("All migrations ran successfully")
