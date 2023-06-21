import logging
import sqlite3
import os
import xml.etree.ElementTree as ET

root_dir = os.path.dirname(os.path.abspath(__file__))
xml_dir = os.path.join(root_dir, 'xml')

# comb through all of my xml files and load them into a sqlite database
# this is a one-time thing, so it's not optimized for speed

db = sqlite3.connect(os.path.join(root_dir, 'db.sqlite3'))

# create the table
db.execute('''
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(64) NOT NULL,
        parent_id INTEGER,
        has_name INTEGER NOT NULL default 0,
        FOREIGN KEY(parent_id) REFERENCES categories(id) ON DELETE CASCADE
    )
    ''')

db.execute('''
    CREATE TABLE IF NOT EXISTS rolltable (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(255) NOT NULL,
        category_id INTEGER NOT NULL,
        FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE CASCADE
    )
    ''')

db.execute('''
    CREATE TABLE IF NOT EXISTS rolltable_entry (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rolltable_id INTEGER NOT NULL,
        value VARCHAR(255) NOT NULL,
        FOREIGN KEY(rolltable_id) REFERENCES rolltable(id) ON DELETE CASCADE
    )
    ''')

db.execute('''
    CREATE TABLE IF NOT EXISTS rolltable_entry_regions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rolltable_entry_id INTEGER NOT NULL,
        region_start INTEGER NOT NULL,
        region_end INTEGER NOT NULL,
        rolltable_id INTEGER NOT NULL,
        FOREIGN KEY(rolltable_id) REFERENCES rolltable(id) ON DELETE CASCADE,
        FOREIGN KEY(rolltable_entry_id) REFERENCES rolltable_entry(id) ON DELETE CASCADE
    )
    ''')

db.execute('''
    CREATE TABLE IF NOT EXISTS rolltable_includes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rolltable_id INTEGER NOT NULL,
        include_rolltable_id INTEGER NOT NULL,
        FOREIGN KEY(rolltable_id) REFERENCES rolltable(id) ON DELETE CASCADE,
        FOREIGN KEY(include_rolltable_id) REFERENCES rolltable(id) ON DELETE CASCADE
    )
    ''')

# load the xml files
for filename in os.listdir(xml_dir):
    print('Processing {}'.format(filename))
    tree = ET.parse(os.path.join(xml_dir, filename))  # parse the xml file into a tree
    # insert into db
    db.execute('INSERT INTO categories (name, parent_id, has_name) VALUES (?, ?, ?)', (root.attrib["name"], None, 0))
    # get insert id
    category_id = db.lastrowid

    root = tree.getroot()  # get the root of the tree
    for node in root.findall('table'):
        # get the table name
        table_name = node.get('name')
        # insert into db
        db.execute('INSERT INTO rolltable (name, category_id) VALUES (?, ?)', (table_name, category_id))
        table_id = db.lastrowid

        for value in node.findall('value'):
            region_start = value.attrib['region_start']
            region_end = value.attrib['region_end']
            region_include = value.attrib['region_include']
            # insert into db
            db.execute('INSERT INTO rolltable_entry (rolltable_id, value) VALUES (?, ?)', (table_id, value.text))
            rolltable_entry_id = db.lastrowid
