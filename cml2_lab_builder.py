#!/usr/bin/env python3
"""
Creates a CML2 lab with all needed nodes, interfaces and links.
Loads Cisco configuration files and modifies them to match the CML2 lab.
Creates a Cisco pyATS testbed file.
For more information, read the documentation on Github.
"""

import os
import sys
import argparse
import timeit
import json
import yaml
import ipaddress
from virl2_client import ClientLibrary
from virl2_client import exceptions
from requests.exceptions import HTTPError
from ciscoconfparse import CiscoConfParse
from alive_progress import alive_bar
from genie import testbed


__author__ = 'Willi Kubny'
__version__ = '1.1'


# Start the lab build timer
lab_start_time = timeit.default_timer()


def print_colored(message, color=None, style=None):
    """
    Prints text in different styles. Available parameters are:
    color = blue/cyan/green/yellow/red
    style = bold/underline
    """
    # Set the color and style
    if color == 'blue':
        sys.stdout.write('\033[94m')
    if color == 'cyan':
        sys.stdout.write('\033[96m')
    if color == 'green':
        sys.stdout.write('\033[92m')
    if color == 'yellow':
        sys.stdout.write('\033[93m')
    if color == 'red':
        sys.stdout.write('\033[91m')
    if style == 'bold':
        sys.stdout.write('\033[1m')
    if style == 'underline':
        sys.stdout.write('\033[4m')

    # Print the message with the defined color and style
    print(message)

    # Set the color and style back to default
    sys.stdout.write('\033[0m')


def task_title(title):
    """
    Prints the Task title to shell
    """
    # Get shell window width and height
    terminal_size = os.get_terminal_size()
    # Get length of the Task heading string
    heading = f'TASK [{title}]'
    heading_length = (len(heading))
    # Get a terminal wide asterisk line minus the length of the heading length
    asterisk_line = ((terminal_size.columns - heading_length) * '*')
    # Print the heading followed by the aserisk line to shell
    bold = '\033[1m'
    bold_end = '\033[0m'
    print(f'\n{bold}{heading}{asterisk_line}{bold_end}\n')


def task_ok(message, hostname=None):
    """
    Prints an OK message to shell
    """
    green = '\033[92m'
    green_end = '\033[0m'
    if hostname:
        print(f'{green}OK: [{hostname}: {message}]{green_end}')
    else:
        print(f'{green}OK: [{message}]{green_end}')


def task_failed(message, hostname=None):
    """
    Prints a Failed message to shell
    """
    red = '\033[91m'
    red_end = '\033[0m'
    if hostname:
        print(f'{red}Failed: [{hostname}: {message}]{red_end}')
    else:
        print(f'{red}Failed: [{message}]{red_end}')


def task_debug(message, hostname=None):
    """
    Prints a Debug output to shell
    """
    cyan = '\033[96m'
    cyan_end = '\033[0m'
    if hostname:
        print(f'{cyan}Debug: [{hostname}]\n{message}{cyan_end}')
    else:
        print(f'{cyan}Debug:\n{message}{cyan_end}')


def read_yaml_to_var(file_path):
    """
    Read the yaml file into a variable.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as stream:
            yaml_var = yaml.safe_load(stream)
        task_ok(f'Loaded file {file_path}', 'CML2')
    except yaml.parser.ParserError as err:
        task_failed(f'{err}', 'CML2')
        remove_lab(lab)
        sys.exit()
    except FileNotFoundError as err:
        task_failed(f'{err}', 'CML2')
        remove_lab(lab)
        sys.exit()

    return yaml_var


def remove_lab(lab_object):
    """
    Stop, wipe and delete the lab and print the result to stdout
    """
    lab_object.stop()
    lab_object.wipe()
    lab_object.remove()
    task_ok(f'Deleted lab ID {lab.id}', 'CML2')


def conf_parse_replace_lines_with_regex(parser, find, match, replace):
    """
    Parse config, find object, match a part in the object and replace it.
    parse -> ciscoconfparse parser object
    find -> raw string with/without regex to find object
    match -> raw string with/without regex to match
    replace -> raw string with/without regex to replace
    """
    parsed_objects = parser.find_objects(find)
    object_list = []
    # Loop over all objects which the parser found
    for item in parsed_objects:
        item.replace(match, replace)
        object_list.append(item.text)
    # Commit changes to the parser
    parse.commit()

    return object_list


# Define the arguments which needs to be given to the script execution
argparser = argparse.ArgumentParser(
    description='''Creates a CML2 lab from a hosts.yaml, a links.yaml file
    and optional day 0 device configurations files.'''
)
# Add a script parser argument
argparser.add_argument('--day0', help='Optional: Enable day 0 configuration', required=False)
argparser.add_argument('--oob', help='Optional: Create an OOB VRF with external connection', required=False)
argparser.add_argument('--debug', help='Optional: Enable stdout debug print', required=False)

# Parse the script arguments
args = argparser.parse_args()

# If the --day0 argument is set, verify that the argument is "enable"
if args.day0 and (args.day0 != 'enable'):
        argparser.error('For argument --day0 please specify "enable".')

# If the --oob argument is set, verify that the argument is "enable"
if args.oob and (args.oob != 'enable'):
        argparser.error('For argument --oob please specify "enable".')

# If the --debug argument is set, verify that the argument is "enable"
if args.debug and (args.debug != 'enable'):
        argparser.error('For argument --debug please specify "enable".')

# Print the task title
task_title('Initializing CML2 Server Connection')

# Verify that environment variables are set to connect to the CML2 server
# Raise a KeyError when environment variable is None and stop the script
try:
    cml_server = os.environ['VIRL2_URL']
    task_ok('Loaded environment variable VIRL2_URL')
    cml_user = os.environ['VIRL2_USER']
    task_ok('Loaded environment variable VIRL2_USER')
    cml_password = os.environ['VIRL2_PASS']
    task_ok('Loaded environment variable VIRL2_PASS')

except KeyError as err:
    task_failed(f'Environment variable {err} not found')
    sys.exit()

# Connect to the CML2 server
cml = ClientLibrary(
    cml_server,
    cml_user,
    cml_password,
    ssl_verify=False
    )

# Create the CML2 lab
try:
    lab = cml.create_lab()
    lab.title = f'Lab_ID_{lab.id}'

    # Print the result to stdout
    task_ok('Initialized CML2 server connection', 'CML2')
    task_ok(f'Created lab ID {lab.id}', 'CML2')

except HTTPError as err:
    task_failed(f'{err}', 'CML2')
    sys.exit()

# Read the inventory/hosts.yaml file into a variable as dictionary
hosts_dict = read_yaml_to_var('inventory/hosts.yaml')
# Uncomment for details. Dump the modified dictionary to stdout
if args.debug:
    task_debug(json.dumps(hosts_dict, sort_keys=True, indent=4))

# Read the inventory/links.yaml file into a variable as dictionary
link_dict = read_yaml_to_var('inventory/links.yaml')
# Uncomment for details. Dump the modified dictionary to stdout
if args.debug:
    task_debug(json.dumps(link_dict, sort_keys=True, indent=4))

if args.oob:
    # Read the inventory/oob.yaml file into a variable as dictionary
    oob_var_dict = read_yaml_to_var('inventory/oob.yaml')
    # Uncomment for details. Dump the modified dictionary to stdout
    if args.debug:
        task_debug(json.dumps(oob_var_dict, sort_keys=True, indent=4))

# Print the task title
task_title(f'Setup CML2 Lab ID {lab.id}')

# Prepare the hosts dictionary with nodes for the OOB network
if args.oob:
    # Add an unmanaged switch for OOB access to the topology
    hosts_dict['SW-OOB'] = {}
    hosts_dict['SW-OOB']['data'] = {}
    hosts_dict['SW-OOB']['data']['cml_label'] = 'SW-OOB'
    hosts_dict['SW-OOB']['data']['cml_platform'] = 'unmanaged_switch'
    hosts_dict['SW-OOB']['data']['cml_position'] = [-800, 0]

    # Create a variable for the unmanaged switch hostname
    unmanaged_switch = hosts_dict['SW-OOB']['data']['cml_label']

    # Add an external connector for OOB access to the topology
    hosts_dict['EXT-CONN'] = {}
    hosts_dict['EXT-CONN']['data'] = {}
    hosts_dict['EXT-CONN']['data']['cml_label'] = 'EXT-CONN'
    hosts_dict['EXT-CONN']['data']['cml_platform'] = 'external_connector'
    hosts_dict['EXT-CONN']['data']['cml_position'] = [-1000, 0]

    # Create a variable for the external connector hostname
    external_connector = hosts_dict['EXT-CONN']['data']['cml_label']

# Loop over all hosts in inventory/hosts.yaml and create nodes
try:
    for host in hosts_dict:
        lab.create_node(
            hosts_dict[host]['data']['cml_label'],
            hosts_dict[host]['data']['cml_platform'],
            hosts_dict[host]['data']['cml_position'][0],
            hosts_dict[host]['data']['cml_position'][1]
        )

        # Create with globals() the hostname as variable without dashes
        # This serves as a host specific interface counter when creating links
        globals()[host.replace('-', '')] = 1

        # Print the result to stdout
        task_ok('Created node', host)

        # Uncomment for details. Dump the modified dictionary to stdout
        if args.debug:
            task_debug(json.dumps(hosts_dict[host]['data'], sort_keys=True, indent=4))

except HTTPError as err:
    # Print the result to stdout
    task_failed(f'{err}', host)
    remove_lab(lab)
    sys.exit()

# Prepare the links dictionary with links for the OOB network
if args.oob:
    for host in hosts_dict:
        if host in external_connector:
            # Create with globals() the hostname as variable without dashes
            # This serves as a host specific interface counter for the external connector
            globals()[host.replace('-', '')] = 0

        # Exclute the unmanaged switch and the external connector to not connect each
        # node to the unmanaged switch but not to itself
        if host not in (unmanaged_switch or external_connector):
            # Create a dictionary with the link for each host to the unmanaged switch
            oob_link = {'host_a' : host, 'host_b' : unmanaged_switch}

            # Insert the dictionary to the list of links as the first element
            # The first links are the OOB links followed by the regular node links
            link_dict['link_list'].insert(0, oob_link)

# Loop over all links in inventory/links.yaml and create links
try:
    # The link ID will later be used to map the generated links by cml
    link_id = 0

    # Loop over all links in the inventory/links.yaml file
    for link in link_dict['link_list']:
        # Create two node objects
        node_a = lab.get_node_by_label([link][0]['host_a'])
        node_b = lab.get_node_by_label([link][0]['host_b'])

        for host in hosts_dict:
            if host == [link][0]['host_a']:
                # Create an interface on both nodes and specify the slot number to start
                # With this the mgmt0 interface won't be used as the first interface
                node_a_i1 = lab.create_interface(node_a, globals()[host.replace('-', '')])

                # Increase the host specific interface counter
                globals()[host.replace('-', '')] += 1

        for host in hosts_dict:
            if host == [link][0]['host_b']:
                # Create an interface on both nodes and specify to start with slot 1
                # With this the mgmt0 interface won't be used as the first interface
                node_b_i1 = lab.create_interface(node_b, globals()[host.replace('-', '')])

                # Increase the host specific interface counter
                globals()[host.replace('-', '')] += 1

        # Create the link between both node objects
        lab.create_link(node_a_i1, node_b_i1)

        # Create new key link_id and number each link id start from l0
        # The link ID will be used to map the generated link ids by cml
        [link][0]['link_id'] = f'l{link_id}'

        # Print the result to stdout
        task_ok(f'Created link l{link_id} ', f'{node_a.label} <-> {node_b.label}')

        # Increase link id by one
        link_id += 1

        # Uncomment for details. Dump the modified dictionary to stdout
        if args.debug:
            task_debug(json.dumps(link, sort_keys=True, indent=4))

except exceptions.NodeNotFound as err:
    # Print the result to stdout
    task_failed('Node not found. Link could not be created', err)
    remove_lab(lab)
    sys.exit()

# With this block the cml lab interface details will be added to the link_dict
# Loop over all links in the lab
for cml_link in lab.links():
    # Loop over all links in the inventory/links.yaml file
    for link in link_dict['link_list']:
        # Verify that the link id from the inventory/links.yaml file
        # is identical with the cml lab link id
        if str([link][0]['link_id']) == cml_link.id:
            # Add additional key, value pair to the dictionary to
            # match the config file interface with the cml lab interface
            [link][0]['cml_link_id'] = cml_link.id
            [link][0]['cml_interface_a'] = cml_link.interface_a.label
            [link][0]['cml_interface_b'] = cml_link.interface_b.label

            # Create two node objects for the following print_helper output
            node_a = lab.get_node_by_label([link][0]['host_a'])
            node_b = lab.get_node_by_label([link][0]['host_b'])

            # Print the result to stdout
            task_ok(
                'Added dynamic CML2 link details to dictionary',
                f'{node_a.label} <-> {node_b.label}'
            )

            # Uncomment for details. Dump the modified dictionary to stdout
            if args.debug:
                task_debug(json.dumps(link, sort_keys=True, indent=4))

if args.oob:
    # Clean-up to continue the script properly for all argument variations
    # Copy link_dict dictionary
    oob_link_dict = link_dict.copy()

    # List comprehension to have only the OOB links in the dictionary
    oob_link_dict['link_list'] = [i for i in oob_link_dict['link_list'] if not ((i['host_b'] or i['host_b']) != unmanaged_switch)]

    # Clean-Up link_dict dictionary and remove all OOB network links
    link_dict['link_list'] = [i for i in link_dict['link_list'] if not ((i['host_a'] and i['host_b']) == unmanaged_switch)]

    # Delete the unmanaged switch and the external connector from the hosts_dict
    del hosts_dict['SW-OOB']
    del hosts_dict['EXT-CONN']

if (args.day0 and args.oob) or (args.day0 or args.oob):
    # Print the task title
    task_title(f'Prepare Node Configuration for Lab ID {lab.id}')

if args.day0:
    try:
        # Loop over all hosts in inventory/hosts.yaml to modify the configuration stored
        # in the /config directory. Then write the day 0 config to a temporary file.
        for host in hosts_dict:
            # Create the CiscoConfParse object
            parse = CiscoConfParse(f'config/{host}')

            # Print the result to stdout
            task_ok(f'Start parsing config/{host} configuration file', host)

            # Apply all general configuration modifications here:

            all_general_changes = []

            # nexusv9000, nxosv
            # Finds the first line which start with username
            if parse.has_line_with(r'^username.*role.*'):
                # append_line() adds a line at the bottom of the configuration
                # Add a new cmladmin user
                nexus_cml_user = parse.append_line(
                    'username cmladmin password 0 cisco4ever! role network-admin'
                )
                all_general_changes.append(nexus_cml_user.text)

                # Commit changes to the parser
                parse.commit()

            # iosv, iosvl2
            # Finds the first line which start with username
            if parse.has_line_with(r'^username (\S+) privilege'):
                # append_line() adds a line at the bottom of the configuration
                # Add a new cmladmin user
                ios_cml_user = parse.append_line(
                    'username cmladmin privilege 15 secret 0 cisco4ever!'
                )
                all_general_changes.append(ios_cml_user.text)

                # Commit changes to the parser
                parse.commit()

            # Change enable secret to cisco4ever!
            ios_changed_enable_secret = conf_parse_replace_lines_with_regex(
                parse,
                r'^enable secret',
                r'secret.*$',
                r'secret 0 cisco4ever!'
            )
            all_general_changes.append(ios_changed_enable_secret)

            # Change enable password to cisco4ever!
            ios_changed_enable_pw = conf_parse_replace_lines_with_regex(
                parse,
                r'^enable password',
                r'password.*$',
                r'secret 0 cisco4ever!'
            )
            all_general_changes.append(ios_changed_enable_pw)

            # Print the result to stdout
            task_ok('Applied general node configuration modifications', host)

            # Uncomment for details. Dump the modified dictionary to stdout
            if args.debug:
                task_debug(json.dumps(all_general_changes, sort_keys=True, indent=4), host)

            # 2. Clean-up not needed interfaces for the cml lab

            # Find all interfaces and sub-interfaces which are needed in the configuration
            # with help of the link.yaml file and create a list of interfaces
            all_inventory_interfaces = []
            for link in link_dict['link_list']:
                # Check if the host in the link iteration matches with the host in the
                # host iteration and set the variables to select only correct links.
                if host == [link][0]['host_a']:
                    # Setup all variables for host_a
                    interface_a = [link][0]['interface_a']

                    # Find interfaces that match exactly to the value from the link_list dict
                    for block in parse.find_objects(fr'^interface[\s]{interface_a}$'):
                        all_inventory_interfaces.append(block.text)
                    # Commit changes to the parser
                    parse.commit()

                    # Find sub-interfaces that match to the value from the link_list dict
                    for block in parse.find_objects(fr'^interface[\s]{interface_a}(\.\d+)$'):
                        all_inventory_interfaces.append(block.text)
                    # Commit changes to the parser
                    parse.commit()

                if host == [link][0]['host_b']:
                    # Setup all variables for host_b
                    interface_b = [link][0]['interface_b']

                    # Find interfaces that match exactly to the value from the link_list dict
                    for block in parse.find_objects(fr'^interface[\s]{interface_b}$'):
                        all_inventory_interfaces.append(block.text)
                    # Commit changes to the parser
                    parse.commit()

                    # Find sub-interfaces that match to the value from the link_list dict
                    for block in parse.find_objects(fr'^interface[\s]{interface_b}(\.\d+)$'):
                        all_inventory_interfaces.append(block.text)
                    # Commit changes to the parser
                    parse.commit()

            # Print the result to stdout
            task_ok('Prepared all needed interfaces', host)

            # Uncomment for details. Dump the modified dictionary to stdout
            if args.debug:
                task_debug(json.dumps(all_inventory_interfaces, sort_keys=True, indent=4), host)

            # Delete all interfaces and sub-interfaces which are not needed in the
            # configuration with help of the all_inventory_interfaces list
            all_deleted_interfaces = []
            # Fine all interfaces that contain Ethernet
            for block in parse.find_objects(r'^interface.+?Ethernet.*'):
                # Delete all interfaces with its children from the configuration
                if block.text not in all_inventory_interfaces:
                    all_deleted_interfaces.append(block.text)
                    block.delete()
            # Commit changes to the parser
            parse.commit()

            # Fine all interfaces that contain GigE
            for block in parse.find_objects(r'^interface.+?GigE.*'):
                # Delete all interfaces with its children from the configuration
                if block.text not in all_inventory_interfaces:
                    all_deleted_interfaces.append(block.text)
                    block.delete()
            # Commit changes to the parser
            parse.commit()

            # Print the result to stdout
            task_ok('Deleted all not needed interfaces', host)

            # Uncomment for details. Dump the modified dictionary to stdout
            if args.debug:
                task_debug(json.dumps(all_deleted_interfaces, sort_keys=True, indent=4), host)

            # 3. Prepare interfaces to match the dynamically generated interfaces from CML2

            # Change all needed interface names from the link_dict to the dynamically
            # generated interfaces from cml
            all_changed_interfaces = []
            for link in link_dict['link_list']:
                # Check if the host in the link iteration matches with the host in the
                # host iteration and set the variables to select only correct links.

                if host == [link][0]['host_a']:
                    # Setup all variables for host_a
                    host_a = [link][0]['host_a']
                    interface_a = [link][0]['interface_a']
                    cml_interface_a = [link][0]['cml_interface_a']

                    # Find interfaces in the configuration file and replace them with the
                    # generated cml interface. This also works for sub-interfaces
                    changed_interfaces_host_a = parse.replace_lines(
                        f'interface {interface_a}',
                        f'interface {cml_interface_a}',
                        exactmatch=False
                    )
                    all_changed_interfaces.extend(changed_interfaces_host_a)
                    # Commit changes to the parser
                    parse.commit()

                if host == [link][0]['host_b']:
                    # Setup all variables for host_b
                    host = [link][0]['host_b']
                    interface_b = [link][0]['interface_b']
                    cml_interface_b = [link][0]['cml_interface_b']

                    # Find interfaces in the configuration file and replace them with the
                    # generated cml interface. This also works for sub-interfaces
                    changed_interfaces_host_b = parse.replace_lines(
                        f'interface {interface_b}',
                        f'interface {cml_interface_b}',
                        exactmatch=False
                    )
                    all_changed_interfaces.extend(changed_interfaces_host_b)
                    # Commit changes to the parser
                    parse.commit()

            # Print the result to stdout
            task_ok('Modified all needed interfaces to match the dynamic CML2 interfaces', host)

            # Uncomment for details. Dump the modified dictionary to stdout
            if args.debug:
                task_debug(json.dumps(all_changed_interfaces, sort_keys=True, indent=4), host)

            # Apply further interface modifications here:

            # Save the modified config to file
            parse.save_as(f'config/cml2_{host}')

            if not args.oob:
                # Print the result to stdout
                task_ok(f'Created temporary node configuration file config/cml2_{host}', host)

    except FileNotFoundError as err:
        # Print the result to stdout
        task_failed(f'{err}', host)
        remove_lab(lab)
        sys.exit()

if args.oob:
    # Create the OOB network and verify its a correct network address and subnet mask
    try:
        oob_vlan_subnet = ipaddress.ip_network(oob_var_dict['oob_vlan_subnet'])

    except ValueError as err:
        # Print the result to stdout
        task_failed(f'OOB network {err}', 'CML2')
        remove_lab(lab)
        sys.exit()

    # Create the OOB default-gateway and verify its a correct IP-Address
    try:
        oob_vlan_gateway = ipaddress.ip_address(oob_var_dict['oob_vlan_gateway'])

    except ValueError as err:
        # Print the result to stdout
        task_failed(f'OOB IP-Address {err}', 'CML2')
        remove_lab(lab)
        sys.exit()

    # Verify that the default-gateway is in the OOB vlan host ip range
    if oob_vlan_gateway in ipaddress.ip_network(oob_var_dict['oob_vlan_subnet']):
        pass
    else:
        # Print the result to stdout
        task_failed(f'Default-Gateway {oob_vlan_gateway} is not in OOB Vlan {oob_vlan_subnet}', 'CML2')
        remove_lab(lab)
        sys.exit()

    # Create the OOB vlan number and verify the vlan tag is between 1 and 4094
    oob_vlan_number = oob_var_dict['oob_vlan_number']
    if 1 <= oob_vlan_number <= 4094:
        pass
    else:
        # Print the result to stdout
        task_failed(f'OOB VLAN number {oob_vlan_number} is not between 1 and 4094', 'CML2')
        remove_lab(lab)
        sys.exit()

    # Create OOB Configuration
    try:
        # Loop over all hosts in inventory/hosts.yaml to create the OOB configuration
        for host in hosts_dict:
            # If the host configuration file exists
            if not os.path.exists(f'config/cml2_{host}'):
                # Create a new host configuration file
                open(f'config/cml2_{host}', 'a').close()

                # Print the result to stdout
                task_ok('Created empty node configuration file', host)

                # Print the result to stdout
                task_ok(f'Start editing config/cml2_{host} configuration file', host)

            # Search the first tree IP-Adress to assign to the node
            for ip in oob_vlan_subnet.hosts():
                if ip == oob_vlan_gateway:
                    print(ip)
                    pass
                else:
                    oob_ip = ip
                    print(f'First free IP-Address is {ip}')
                    break

            # Create the CiscoConfParse object
            parse = CiscoConfParse(f'config/cml2_{host}')

            node_platform = hosts_dict[host]['data']['cml_platform']
            oob_interface = 'Ethernet1/1'

            all_oob_changes = []

            # OOB configuration
            if node_platform == ('nxosv9000' or 'nxosv'):
                oob_config = [
                    f'hostname {host}',
                    '!',
                    'feature interface-vlan',
                    '!',
                    'vrf definition CML2-OOB',
                    ' description CML2-OOB',
                    '!',
                    f'vlan {oob_vlan_number}',
                    ' name CML2-OOB',
                    '!',
                    f'interface vlan {oob_vlan_number}',
                    ' vrf member CML2-OOB',
                    ' description CML2-OOB',
                    f' ip address {oob_ip} {oob_vlan_subnet.netmask}',
                    ' no shutdown',
                    '!',
                    f'interface {oob_interface}',
                    ' switchport',
                    f' switchport access vlan {oob_vlan_number}',
                    ' spanning-tree port type edge',
                    ' no shutdown',
                    '!',
                    f'ip route 0.0.0.0 0.0.0.0 {oob_vlan_gateway} vrf CML2-OOB',
                    '!'
                ]

                # Loop over the list of configuration lines
                for line in oob_config:
                    # append_line() adds a line at the bottom of the configuration
                    config_line = parse.append_line(line)
                    all_oob_changes.append(config_line.text)

            # Commit changes to the parser
            parse.commit()

            # Print the result to stdout
            task_ok('Created oob node configuration', host)

            # Uncomment for details. Dump the modified dictionary to stdout
            if args.debug:
                task_debug(json.dumps(all_oob_changes, sort_keys=True, indent=4), host)

            # Save the modified config to file
            parse.save_as(f'config/cml2_{host}')

            # Print the result to stdout
            task_ok(f'Created temporary node configuration file config/cml2_{host}', host)

    except FileNotFoundError as err:
        # Print the result to stdout
        task_failed(f'{err}', host)
        remove_lab(lab)
        sys.exit()

if (args.day0 and args.oob) or (args.day0 or args.oob):
    # Print the task title
    task_title(f'Apply Node Configuration for Lab ID {lab.id}')

if args.oob:
    # Use globals() to set the variable name to the hostname without
    # any dash and create a node object by finding the node by its label
    globals()[host.replace('-', '')] = lab.get_node_by_label(external_connector)

    # Set the external connector mode to bridge0
    # .config expects a string
    globals()[host.replace('-', '')].config = 'bridge0'

    # Print the result to stdout
    task_ok('Applied node configuration', external_connector)

if (args.day0 and args.oob) or (args.day0 or args.oob):
    # Loop over all hosts in inventory/hosts.yaml and apply the new created day 0 configuration
    try:
        for host in hosts_dict:
            # Use globals() to set the variable name to the hostname without
            # any dash and create a node object by finding the node by its label
            globals()[host.replace('-', '')] = lab.get_node_by_label(host)

            # Read new day 0 config file line by line into a list of strings
            with open(f'config/cml2_{host}', 'r', encoding='utf-8') as stream:
                config_line_list = stream.readlines()

            # Construct from the list of strings a string with multiple lines
            config_line_string = ''.join([str(item) for item in config_line_list])

            # Apply the day 0 configuration to the switch
            # .config expects a string
            globals()[host.replace('-', '')].config = config_line_string

            # Print the result to stdout
            task_ok('Applied node configuration', host)

            # Delete the pyATS testbed file from the filesystem
            os.remove(f'config/cml2_{host}')

            # Print the result to stdout
            task_ok(f'Deleted temporary node configuration file config/cml2_{host}', host)

    except FileNotFoundError as err:
        # Print the result to stdout
        task_failed(f'{err}', host)
        remove_lab(lab)
        sys.exit()

# Print task title
task_title(f'Start CML2 Lab ID {lab.id}')

# Start the CML2 lab and show the progress bar
try:
    # Set stdout print to green
    sys.stdout.write('\033[92m')

    with alive_bar(
            title=f'Lab ID {lab.id} is starting ...',
            spinner='waves2',
            unknown='waves2') as bar:
        lab.start()

    # Set stdout print back to default
    sys.stdout.write('\033[0m')

    # Print the result to stdout
    task_ok(f'Started CML2 lab {lab.title} - ID {lab.id}', 'CML2')

except:
    print('\n')
    # Print the result to stdout
    task_failed(f'Lab ID {lab.id} could not be started', 'CML2')
    remove_lab(lab)
    sys.exit()

# Stop the lab build timer
lab_stop_time = timeit.default_timer()

if args.day0:
    # Print the task title
    task_title(f'Initializing pyATS Testbed for Lab ID {lab.id}')

    # Start the pyATS automation timer
    pyats_start_time = timeit.default_timer()

    # Generate a pyATS testbed on the CML2 server
    testbed_generated = lab.get_pyats_testbed()

    # Print the result to std-out
    task_ok('Generated temporary pyATS testbed on CML2 server', 'CML2')

    # Write the generated pyATS testbed to a temporary file
    with open(f'inventory/tmp_pyats_testbed_{lab.id}.yaml', 'w', encoding='utf-8') as stream:
        stream.write(testbed_generated)

    # Read the temporary pyATS testbed as yaml into a variable to do modifications
    with open(f'inventory/tmp_pyats_testbed_{lab.id}.yaml', 'r', encoding='utf-8') as stream:
        testbed_loaded = yaml.safe_load(stream)

    # Print the result to std-out
    task_ok('Loaded temporary pyATS testbed for modifications', 'CML2')

    # Change the default terminal server username and password to look for the cml environment variables
    testbed_loaded['devices']['terminal_server']['credentials']['default']['username'] = '%ENV{VIRL2_USER}'
    testbed_loaded['devices']['terminal_server']['credentials']['default']['password'] = '%ENV{VIRL2_PASS}'

    # Print the result to std-out
    task_ok('Modified terminal server username and password', 'CML2')

    # Uncomment for details. Dump the modified dictionary to stdout
    if args.debug:
        task_debug(json.dumps(
            testbed_loaded['devices']['terminal_server'], sort_keys=True, indent=4
            ), 'CML2'
        )

    # Print the result to std-out
    task_ok('Modified devices default credentials for the user cmladmin', 'CML2')

    # Changes for each node in the testbed
    for node in testbed_loaded['devices']:
        if 'terminal_server' not in node:
            # Change the key from series to platform as series has been deprecated
            testbed_loaded['devices'][node]['platform'] = testbed_loaded['devices'][node]['series']
            # Delete the key series
            del testbed_loaded['devices'][node]['series']
            # Change the default credentials
            testbed_loaded['devices'][node]['credentials']['default']['username'] = 'cmladmin'
            testbed_loaded['devices'][node]['credentials']['default']['password'] = 'cisco4ever!'

            # Uncomment for details. Dump the modified dictionary to stdout
            if args.debug:
                task_debug(json.dumps(
                    testbed_loaded['devices'][node], sort_keys=True, indent=4
                    ), node
                )

    # Write the modified pyATS testbed to a file
    with open(f'inventory/pyats_testbed_{lab.id}.yaml', 'w', encoding='utf-8') as stream:
        yaml.dump(testbed_loaded, stream, default_flow_style=False)

    # Print the result to std-out
    task_ok(f'Saved final pyATS testbed inventory/pyats_testbed_{lab.id}.yaml', 'CML2')

    # Delete the temporary pyATS testbed file from the filesystem
    os.remove(f'inventory/tmp_pyats_testbed_{lab.id}.yaml')

    # Print the result to std-out
    task_ok('Deleted temporary pyATS testbed from filesystem', 'CML2')

    # Print task title
    task_title(f'Demo: pyATS on Nodes in Lab ID {lab.id}')

    # Step 0: Load the pyATS testbed
    testbed = testbed.load(testbed_loaded)
    # Print the result to std-out
    task_ok(f'Loaded pyATS testbed inventory/pyats_testbed_{lab.id}.yaml', 'CML2')
    print('\n')

    for host in hosts_dict:
        # Step 1: The testbed is a dictionary. Extract the device hostname and create an object
        switch = testbed.devices[host]

        # Print the result to std-out
        task_ok('Extracted the device hostname and create an object', host)

        # Step 2: Connect to the device
        switch.connect(init_exec_commands=[], init_config_commands=[], log_stdout=False)
        # Print the result to std-out
        task_ok('Connected to the device', host)

        # Step 3: Parsing output of show version into a dictionary
        command = switch.parse('show version')
        # Print the result to std-out
        task_ok('Parsing output of show version into a dictionary', host)
        if args.debug:
            print_colored(json.dumps(command, sort_keys=True, indent=4), 'cyan')

        # Step 5: Disconnect from the device
        switch.disconnect()
        # Print the result to std-out
        task_ok('Disconnected from the device', host)
        print('\n')

# Print the task title
task_title('CML2 Lab Builder Recap')

# Calculate lab build timer and prepare for a nice output
lab_total_running_time = lab_stop_time - lab_start_time
lab_minutes, lab_seconds = divmod(lab_total_running_time, 60)
lab_hours, lab_minutes = divmod(lab_minutes, 60)

# Print the total CML2 lab build time
sys.stdout.write(
    '\033[92m'
    'Total CML2 Lab Build Time: %dm %ds\n'
    '\033[0m' % (lab_minutes, lab_seconds)
)

if args.day0:
    # Stop the pyATS automation timer
    pyats_stop_time = timeit.default_timer()

    # Calculate pyATS automation timer and prepare for a nice output
    pyats_total_running_time = pyats_stop_time - pyats_start_time
    pyats_minutes, pyats_seconds = divmod(pyats_total_running_time, 60)
    pyats_hours, pyats_minutes = divmod(pyats_minutes, 60)

    # Print the total pyATS automation time
    sys.stdout.write(
        '\033[92m'
        'Total pyATS Automation Time: %dm %ds\n\n'
        '\033[0m' % (pyats_minutes, pyats_seconds)
    )

# Print some details about the created CML2 lab
print_colored(
    f'\n'
    f'Title: {lab.title:<22}'
    f'ID: {lab.id:<12}'
    f'URL: {lab.lab_base_url}\n', 'green'
)

# Print some details about each node
for node in lab.nodes():
    print_colored(
        f'Node: {node.label:<22}'
        f'ID: {node.id:<12}'
        f'State: {node.state:<12}'
        f'CPU: {node.cpu_usage:}%', 'green'
    )
print('\n')
