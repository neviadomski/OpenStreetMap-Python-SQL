# -*- coding: utf-8 -*-
"""
Created on Thu Oct 13 18:19:20 2016

@author: Sergei Neviadomski
"""
# Importing needed libraries
import xml.etree.cElementTree as ET
from collections import defaultdict
import re
import pprint
import csv
import codecs
import cerberus
import schema
import sqlite3

#############################################################
#################   OSM FILE CLEANING      ##################
#############################################################


# OSM file
osm_file = "pittsburgh_pennsylvania.osm"

# re function
# Compile a regular expression pattern into a regular expression object  
street_type_re = re.compile(r'\b\S+\.?$', re.IGNORECASE)

# Expected street types list
expected = ["Street", "Avenue", "Boulevard", "Drive", "Court", "Place",
            "Square", "Lane", "Road", "Trail", "Parkway", "Commons", "Alley",
            "Bridge", "Highway", "Circle", "Terrace", "Way"]

# Adding street names in dictionary by type
# Takes 2 arguments: dictionary and string. If string doesn't match pattern 
# adds it to dictionary. 
def audit_street_type(street_types, street_name):
    m = street_type_re.search(street_name)
    if m:
        street_type = m.group()
        if street_type not in expected:
            street_types[street_type].add(street_name)

# Checking tag for street data content 
def is_street_name(elem):
    return (elem.attrib['k'] == "addr:street")

# Auditing file for different abbreviations of same street types 
# Takes osm file as input and returns dictionary of different abbreviations
# of different street types
def audit(osmfile):
    osm_file = open(osmfile, "r")    
    street_types = defaultdict(set)
    for event, elem in ET.iterparse(osm_file, events=("start",)):
        if elem.tag == "node" or elem.tag == "way":
            for tag in elem.iter("tag"):
                if is_street_name(tag):
                    audit_street_type(street_types, tag.attrib['v'])
    osm_file.close()
    return street_types
    
    
# Auditing our osm file
st_types = audit(osm_file)

# Printing results 
pprint.pprint(dict(st_types))

mapping = { "St": "Street",
            "St.": "Street",
            "ST": "Street",
            "Ave": "Avenue",
            "Ave.": "Avenue",
            "Av.": "Avenue",
            "Av": "Avenue",
            "Sq": "Square",
            "CT": "Court",
            "Ct": "Court",
            "DR": "Drive",
            "Dr": "Drive",
            "Dr.": "Drive", 
            "Rd.": "Road",
            "Rd": "Road",
            "Pl": "Place",
            "Hwy": "Highway",
            "Ln": "Lane",
            "Blvd": "Boulevard",
            "Blvd.": "Boulevard",
            "Brdg":"Bridge",
            "Ter": "Terrace" 
            }
            
osm_file_2 = "pittsburgh_pennsylvania_2.osm"

# This function replace abbreviation by full name in string
# Takes as input string and dictionary of abbreviations and returns new string
# with abbreviation replaced by full name from dictionary 
def update_name(name, mapping):
    words = name.split(' ')
    last_word = words[-1]
    if last_word in mapping.keys():
        name2 = name.replace(last_word, mapping[last_word])
        return name2
    return name

# Supporting function to get element from osm file
# Takes as input osm file and tuple of nodes and yield nodes of types from tuple. 
def get_element(osm_file, tags=('node', 'way', 'relation')):
    context = iter(ET.iterparse(osm_file, events=('start', 'end')))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            yield elem
            root.clear()
            
# This function replace abbreviations in osm file
# Takes 2 osm file names as input and replace all abbreviations of streets in 
# first file. Saves new file under new name (new_file)
def modify_street(old_file, new_file):
    with open(new_file, 'wb') as output:
        output.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        output.write('<osm>\n  ') 
        for i, element in enumerate(get_element(old_file)):
            for tag in element.iter("tag"):
                if is_street_name(tag):
                    tag.set('v',update_name(tag.attrib['v'], mapping))
            output.write(ET.tostring(element, encoding='utf-8'))
        output.write('</osm>')

# Modifying osm file
modify_street(osm_file, osm_file_2)


# Checking tag for postcode content 
zip_type_re = re.compile(r'\d{5}-??')

# Sorting zipcodes in different forms and save them to dict
def audit_zip_type(zip_types, zip):
    m = zip_type_re.search(zip)
    if m:
        zip_type = m.group()
        if zip_type not in zip_types:
            zip_types[zip_type].add(zip)
    else:
        zip_types['unknown'].add(zip)

# Checking if tag contains postcode
def is_zip(elem):
    return (elem.attrib['k'] == "addr:postcode")

# Auditing file for different variations of same zip 
def zip_audit(osmfile):
    osm_file = open(osmfile, "r")    
    zip_types = defaultdict(set)
    for event, elem in ET.iterparse(osm_file, events=("start",)):
        if elem.tag == "node" or elem.tag == "way":
            for tag in elem.iter("tag"):
                if is_zip(tag):
                    audit_zip_type(zip_types, tag.attrib['v'])                
    osm_file.close()
    return zip_types
    
# Auditing our osm file
zp_types = zip_audit(osm_file_2)

# Printing results 
pprint.pprint(dict(zp_types))

osm_file_3 = "pittsburgh_pennsylvania_3.osm"

# This function replace abbrevition by right zip
def update_zip(zip):
    m = zip_type_re.search(zip)
    if m:
        return m.group()
    else:
        return 'unknown'

# This function replace wrong zip in osm file
def modify_zip(old_file, new_file):
    with open(new_file, 'wb') as output:
        output.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        output.write('<osm>\n  ') 
        for i, element in enumerate(get_element(old_file)):
            for tag in element.iter("tag"):
                if is_zip(tag):
                    tag.set('v',update_zip(tag.attrib['v']))
            output.write(ET.tostring(element, encoding='utf-8'))
        output.write('</osm>')

# Modifying osm file
modify_zip(osm_file_2, osm_file_3)


# Checking tag for phone content 
phone_type_re = re.compile(r'\d{3}\)?-?\s?.?\d{3}\s?-?\s?.?\d{4}')
# Compiler for cleaning phone in bad format
phone_re = re.compile('\.|\)|\s|-')

# Adding street names in dictionary good_format: original
def audit_phone_type(phone_types, phone):
    m = phone_type_re.search(phone)
    if m:
        phone_type = m.group()
        if phone_type not in phone_types:
            new_phone = phone_re.sub('',phone_type)
            new_phone = ('+1-' + new_phone[:3] + '-' +
                         new_phone[3:6] + '-' + new_phone[6:])
            phone_types[new_phone].add(phone)
    else:
        phone_types['unknown'].add(phone)

# Checking if tag contains phone
def is_phone(elem):
    return (elem.attrib['k'] == "phone")

# Auditing file for different variations of phone type
def phone_audit(osmfile):
    osm_file = open(osmfile, "r")    
    phone_types = defaultdict(set)
    for event, elem in ET.iterparse(osm_file, events=("start",)):
        if elem.tag == "node" or elem.tag == "way":
            for tag in elem.iter("tag"):
                if is_phone(tag):
                    audit_phone_type(phone_types, tag.attrib['v'])                
    osm_file.close()
    return phone_types
    
# Auditing our osm file
ph_types = phone_audit(osm_file_3)

# Printing results 
pprint.pprint(dict(ph_types))

osm_file_4 = "pittsburgh_pennsylvania_4.osm"

# This function updates format of phone numbers to right one. 
def update_phone(phone):
    m = phone_type_re.search(phone)
    if m:
        new_phone = phone_re.sub('', m.group())
        return ('+1-' + new_phone[:3] + '-' + new_phone[3:6] +
                '-' + new_phone[6:])        
    else:
        return phone

# This function replace wrong phone formats in osm file
def modify_phone(old_file, new_file):
    with open(new_file, 'wb') as output:
        output.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        output.write('<osm>\n  ') 
        for i, element in enumerate(get_element(old_file)):
            for tag in element.iter("tag"):
                if is_phone(tag):
                    tag.set('v',update_phone(tag.attrib['v']))
            output.write(ET.tostring(element, encoding='utf-8'))
        output.write('</osm>')



# Modifying osm file
modify_phone(osm_file_3, osm_file_4)
        



#############################################################
###########   PREPARATIONS FOR TRANSFER TO SQL  #############
#############################################################

# Path to new csv files
NODES_PATH = "nodes.csv"
NODE_TAGS_PATH = "nodes_tags.csv"
WAYS_PATH = "ways.csv"
WAY_NODES_PATH = "ways_nodes.csv"
WAY_TAGS_PATH = "ways_tags.csv"

# Regular expression compilers
LOWER_COLON = re.compile(r'^([a-z]|_)+:([a-z]|_)+')
PROBLEMCH = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')

# Importing schema for pransformation from schema.py file
SCHEMA = schema.schema

# Fields of new csv files
# Make sure the fields order in the csvs matches the column order in the 
# sql table schema
NODE_FIELDS = ['id', 'lat', 'lon', 'user', 'uid', 'version',
               'changeset', 'timestamp']
NODE_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_FIELDS = ['id', 'user', 'uid', 'version', 'changeset', 'timestamp']
WAY_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_NODES_FIELDS = ['id', 'node_id', 'position']


# Main function for transformation of XML data to Python dict
def shape_element(element, node_attr_fields=NODE_FIELDS,
                  way_attr_fields=WAY_FIELDS, prob_ch=PROBLEMCH,
                  default_tag_type='regular'):
    
    tag_attribs = {}
    way_nodes = []
    tags = []
    count = 0
    if element.tag == 'node':
        tagfields = node_attr_fields
    elif element.tag == 'way':
        tagfields = way_attr_fields
    
    if element.tag == 'node' or 'way':
        for attrib in element.attrib:
            if attrib in tagfields:
                tag_attribs[attrib] = element.attrib[attrib]
    for subelem in element:
        if subelem.tag == 'tag' and prob_ch.match(subelem.attrib['k']) == None:
            tag = {}
            tag['id'] = tag_attribs['id']
            tag['value'] = subelem.attrib['v']
            key = subelem.attrib['k']
            tag['key'] = key[key.find(':') + 1:]
            if ':' in key:
                tag['type'] = key[:key.find(':')]
            else:
                tag['type'] = default_tag_type
            tags.append(tag)
        elif subelem.tag == 'nd':
            way_node = {}
            way_node['id'] = tag_attribs['id']
            way_node['node_id'] = subelem.attrib['ref']
            way_node['position'] = count
            count += 1
            way_nodes.append(way_node)
    
    if element.tag == 'node':
        return {'node': tag_attribs, 'node_tags': tags}
    elif element.tag == 'way':
        return {'way': tag_attribs, 'way_nodes': way_nodes, 'way_tags': tags}
    
# Validating element to match schema
def validate_element(element, validator, schema=SCHEMA):
    """Raise ValidationError if element does not match schema"""
    if validator.validate(element, schema) is not True:
        field, errors = next(validator.errors.iteritems())
        message_string = "\nElement of type '{0}' has the following errors:\n{1}"
        error_strings = (
            "{0}: {1}".format(k, v if isinstance(v, str) else ", ".join(v))
            for k, v in errors.iteritems()
        )
        raise cerberus.ValidationError(
            message_string.format(field, "\n".join(error_strings))
        )


# Extend csv.DictWriter to handle Unicode input
class UnicodeDictWriter(csv.DictWriter, object):
    def writerow(self, row):
        super(UnicodeDictWriter, self).writerow({
            k: (v.encode('utf-8') if isinstance(v, unicode) else v) for k, v in row.iteritems()
        })

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)
            
# Main function processing osm file to 5 csv files
def process_map(file_in, validate):
    """Iteratively process each XML element and write to csv(s)"""

    with codecs.open(NODES_PATH, 'w') as nodes_file, \
         codecs.open(NODE_TAGS_PATH, 'w') as nodes_tags_file, \
         codecs.open(WAYS_PATH, 'w') as ways_file, \
         codecs.open(WAY_NODES_PATH, 'w') as way_nodes_file, \
         codecs.open(WAY_TAGS_PATH, 'w') as way_tags_file:

        nodes_writer = UnicodeDictWriter(nodes_file, NODE_FIELDS)
        node_tags_writer = UnicodeDictWriter(nodes_tags_file, NODE_TAGS_FIELDS)
        ways_writer = UnicodeDictWriter(ways_file, WAY_FIELDS)
        way_nodes_writer = UnicodeDictWriter(way_nodes_file, WAY_NODES_FIELDS)
        way_tags_writer = UnicodeDictWriter(way_tags_file, WAY_TAGS_FIELDS)

        nodes_writer.writeheader()
        node_tags_writer.writeheader()
        ways_writer.writeheader()
        way_nodes_writer.writeheader()
        way_tags_writer.writeheader()

        validator = cerberus.Validator()

        for element in get_element(file_in, tags=('node', 'way')):
            el = shape_element(element)
            if el:
                if validate is True:
                    validate_element(el, validator)

                if element.tag == 'node':
                    nodes_writer.writerow(el['node'])
                    node_tags_writer.writerows(el['node_tags'])
                elif element.tag == 'way':
                    ways_writer.writerow(el['way'])
                    way_nodes_writer.writerows(el['way_nodes'])
                    way_tags_writer.writerows(el['way_tags'])
                    
# Note: Validation is ~ 15X slower. Consider using a small
# sample of the map when validating.
process_map(osm_file_4, validate=True)

#############################################################
#############   BUILDING SQL DB BY SCHEMA  ##################
#############################################################

# In this section we will build empty SQL database and create table schema.
# We'll use sqlite3 shell for this purpose. It's needed to create DB and 
# read create_db.csv file.
# Next command will execute create_csv.db file by executing next command:
# .read create_csv.db
# This file contains next rows:
###    CREATE TABLE nodes ( id INTEGER PRIMARY KEY NOT NULL, lat REAL, lon REAL, user TEXT, uid INTEGER, version INTEGER, changeset INTEGER, timestamp TEXT );
###    CREATE TABLE nodes_tags ( id INTEGER, key TEXT, value TEXT, type TEXT, FOREIGN KEY (id) REFERENCES nodes(id) );
###    CREATE TABLE ways ( id INTEGER PRIMARY KEY NOT NULL, user TEXT, uid INTEGER, version TEXT, changeset INTEGER, timestamp TEXT );
###    CREATE TABLE ways_tags ( id INTEGER NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL, type TEXT, FOREIGN KEY (id) REFERENCES ways(id) );
###    CREATE TABLE ways_nodes ( id INTEGER NOT NULL, node_id INTEGER NOT NULL, position INTEGER NOT NULL, FOREIGN KEY (id) REFERENCES ways(id), FOREIGN KEY (node_id) REFERENCES nodes(id) );
###    .mode csv
###    .import nodes.csv nodes
###    .import ways.csv ways
###    .import nodes_tags.csv nodes_tags
###    delete from nodes_tags where id = 'id';
###    .import ways_tags.csv ways_tags
###    delete from ways_tags where id = 'id';
###    .import ways_nodes.csv ways_nodes
###    delete from ways_nodes where id = 'id';

#############################################################
#####################   SQLite3 QUERING  ####################
#############################################################
#Esteblishing connection and cursor
conn = sqlite3.connect("osm.db")
cursor = conn.cursor()

#Executing and printing 
cursor.execute("select count(id) from nodes;")
print 'There are {} nodes in database.'.format(cursor.fetchall()[0][0])

cursor.execute("select count(id) from ways;")
print 'There are {} ways in database.'.format(cursor.fetchall()[0][0])

cursor.execute("select count(distinct(uid)) from (select uid from nodes union select uid from ways);")
print 'There are {} uniqe users in database.'.format(cursor.fetchall()[0][0])

cursor.execute("select id, count(*) as nodes_count from ways_nodes group by id order by nodes_count desc limit 1;")
way_id, count = cursor.fetchall()[0]
print "There're {} nodes in the biggest way in database. Way id is {}.".format(count, way_id)

cursor.execute("select * from ways_tags where id = {};".format(way_id))
print 'This way is:'
pprint.pprint(cursor.fetchall())

cursor.execute("select count(key) from ways_tags where key = 'bridge' and value != 'yes' group by key;")
print "There are {} bridges in Pitt. That's a second Venice.".format(cursor.fetchall()[0][0])

cursor.execute("select value, count(*) as count from nodes_tags where key = 'postcode' group by value order by count desc limit 5;")
pprint.pprint(cursor.fetchall())

