# Create a class called DMScreenXML that will read in the XML file
# and represent the file

import xml.etree.ElementTree as ET
import os
import logging
import random

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

class DMScreenXML:
    # Constructor
    def __init__(self, category):
        self.filename = category
        self.root = None
        self.tree = None
        self.parse_xml()

    # Parse the XML file
    def parse_xml(self):
        if os.path.exists(self.filename):
            self.tree = ET.parse(self.filename)
            self.root = self.tree.getroot()
        else:
            logging.error(f"File {self.filename} does not exist.")

    # Get the root element
    def get_root(self):
        return self.root
    
    # Get the tree
    def get_tree(self):
        return self.tree
    
    # Get the number of children of the root element
    def get_num_children(self):
        return len(self.root)
    
    # Get the tables
    def get_tables(self):
        return self.root.findall("table")
    
    # Get the table by name
    def get_table_by_name(self, name):
        return self.root.find(f"table[@name='{name}']")
    
    # Get a random <value> from a table
    def get_random_value(self, table):
        values = table.findall("value")
        return values[random.randint(0, len(values) - 1)].text
    
    # Get all values for this category as a dictionary
    def get_all_values(self):
        values = {}
        for table in self.get_tables():
            if (table.attrib["db"] != "_skip"):
                values[table.attrib["db"]] = self.get_random_value(table)
        return values