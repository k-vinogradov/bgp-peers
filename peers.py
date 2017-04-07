import gspread
import sys

from configparser import ConfigParser
from jinja2 import Environment, FileSystemLoader
from oauth2client.service_account import ServiceAccountCredentials

def error(message):
    print message
    sys.exit(1)


parser = ConfigParser()
parser.read('peers.conf')

scope = parser['spreadsheets']['scope']
key_file = parser['spreadsheets']['keyfile']
sheet_name = parser['spreadsheets']['sheet']
own_as = parser['resources']['as_number']
template_path = parser['local']['templates_path']
credentials = ServiceAccountCredentials.from_json_keyfile_name(key_file, scope)

gc = gspread.authorize(credentials)
wks = gc.open(sheet_name)
wsh = wks.worksheet(sheet_name)
peers_data = wsh.get_all_records()

peers = []

for row in peers_data:
    if row['Status'].lower() == 'active':
        try:
            pid = int(row['ID'])
        except ValueError:
            pid = None
        peers.append(dict(
            configuration_type=row['Configuration Type'].lower(),
            id=pid,
            name=row['Name'].lower(),
            protocol=row['Protocol'].lower(),
            remote_ip=row['Name'].lower() if row['Configuration Type'].lower() == 'group' else row['Remote IP'],
            group_id=row['Group ID'],
            local_as=row['Local AS'],
            remote_as=row['Remote AS'],
            type=row['Neighborship Type'].lower(),
            vrf=row['VRF'],
            max_prefix=row['Maximum Prefixes'],
        ))

for peer in peers:
    if peer['configuration_type'] == 'grouped':
        try:
            group_data = (p for p in peers if p['id'] == int(peer['group_id'])).next()
            peer['group_name'] = group_data['name']
        except StopIteration:
            error('Unknown group ID {0} in the peer # {1}'.format(peer['group_id'], peer['id']))

try:
    name = sys.argv[1].lower()
    data = (p for p in peers if p['name'] == name).next()
except IndexError:
    print 'Available peer names:' 
    for item in peers:
        print '  - ' + item['name']
except StopIteration:
    print 'Available peer names:'
    for item in peers:
        print '  - ' + item['name']
    error('Unknown peer name {}.'.format(sys.argv[1].lower()))
else:
    data['as_number'] = own_as
    peer_type = data['type']
    if data['configuration_type'] == 'grouped':
        template_set = ['configuration']
    else:
        template_set = ['general', 'rm-{}-in'.format(peer_type), 'rm-{}-out'.format(peer_type), 'configuration']

    env = Environment(loader=FileSystemLoader(template_path))
    for template in template_set:
        print env.get_template(template + '.template').render(**data)
sys.exit(0)
