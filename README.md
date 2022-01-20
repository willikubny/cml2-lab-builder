# CML2 Lab Builder

The script helps to automate the initial CML2 lab building process by creating the topology with all its nodes and links. Optional the script can apply the day 0 configuration to each node before the nodes get started.
When the script is executed with the day 0 configuration, then also a pyATS testbed will be created after all CML2 nodes are booted. There are several modifications for the day0 configuration and the pyATS testbed which the script does. These modifications are described later.

## Prerequisites

* You need to run the script against your own CML2 server as it's not allowed to create new labs within the Cisco DevNet CML2 Sandbox
* You need Python 3.5 or higher
* You are ready to create and use a Python virtual environment

## Setting Up your Workstation

1. Setup a Python virtual environment

  	```
  	mkproject cml2_lab_builder
  	```

1. Clone down the repository and change to the directory.

	```
	git clone https://github.com/willikubny/cml2_lab_builder
	cd cml2_lab_builder
	```

1. Install all needed Python libaries.

	```
	pip install -r requirements.txt
	```

## Overview

To see all supported arguments of the script run ```python3 cml2_lab_builder.py --help``` for the following output:

```
usage: cml2_lab_builder.py [-h] [--day0 DAY0] [--debug DEBUG]

Creates a CML2 lab from a hosts.yaml, a links.yaml file and optional day 0 device configurations files.

optional arguments:
  -h, --help     show this help message and exit
  --day0 DAY0    Optional: Enable day 0 configuration
  --debug DEBUG  Optional: Enable stdout debug print.
```

The script needs a `inventory/hosts.yaml` and a `inventory/links.yaml` file to build the CML2 lab topology. If a day 0 configuration should be applied, then the configuration files for each node needs to be present in the `config/` folder.

The repository has an example topology with its `hosts.yaml`, `links.yaml` and the three configuration files `N9K-01`, `N9K-02` and `N9K-03` for the nodes.

```
tree

# Output
.
├── README.md
├── cml2_lab_builder.py
├── config
│   ├── N9K-01
│   ├── N9K-02
│   └── N9K-03
├── inventory
│   ├── hosts.yaml
│   └── links.yaml
└── requirements.txt
```

## Creating the Topology Files

When writing the `hosts.yaml` and `links.yaml` files, its important the the hostname are identical in each file. Otherwise the script will fail. The interfaces in the `links.yaml` file are only needed if the also a day 0 configuration should be applied. The interface value needs to match the interface in the provided configuration file. If no day 0 configuration is needed, the interface value can be blank.

A node definition in the `inventory/hosts.yaml` file:
```yaml
---
# For CML2 only the data dictionary with cml_label, cml_platform
# and cml_position under the hostname is required.
#
# The following is an inventory example to extend the host file and
# connect with Nornir over the CML2 breakout tool to a device.
#
# SW-1:
#  hostname: 127.0.0.1
#  port: 9000
#  username: cisco
#  password: cisco
#  platform: ios
#  connection_options:
#    napalm:
#      extras:
#        optional_args: {'transport': 'telnet'}
#  data:
#     cml_label: SW-1
#     cml_platform: iosvl2
#     cml_position: [0, -100]

N9K-01:
  data:
    cml_label: N9K-01
    cml_platform: nxosv9000
    cml_position: [-300, 0]

```

A link definition in the `links.yaml` file:
```yaml
---
# host_a and host_b are the CML2 nodes where a link will be created.
# interface_a and interface_b needs to match exactly with the provided
# config file, as the script will take these interfaces configurations
# and configure the dynamically assigned interfaces by CML2.
#
# For example:
# - host_a: Hostname-A
#    interface_a: GigabitEthernet1/0/1
#    host_b: Hostname-B
#    interface_b: GigabitEthernet1/0/1

link_list:
  - host_a: N9K-01
    interface_a: Ethernet1/53
    host_b: N9K-02
    interface_b: Ethernet1/51

```

## Applying Configuration Files

When day 0 configuration files should be applied, the filename needs to match the nodes hostname. No modifications should be needed to the configurations files, as the script will know which interfaces are needed for the lab based on the details from the `links.yaml` file. The script will delete all not needed physical port configurations. Further a additional user named `cmladmin` will be created to simplify the pyATS testbed creation.

By default CML2 start to assign the first interface of each node. As the first interface of some nodes is the `mgmt0` interface, the script allways starts with the second interface. This makes it easier to cover different nodes definitions.

The day 0 interface configuration modifications were tested mostly with the following node definitions:
* iosv
* iosvl2
* nxosv
* nxosv9000

## pyATS Testbed Creation

CML2 provides the possibility to generate a pyATS testbed. As this testbed will be generated without any credentials, the script will modify the testbed.

The `terminal_server` credentials will set to `%ENV{VIRL2_USER}` and `%ENV{VIRL2_PASS}` to import the same CML2 login credentials from the environment variables as the script already uses:
```yaml
terminal_server:
    connections:
      cli:
        ip: 10.128.16.51
        protocol: ssh
    credentials:
      default:
        password: '%ENV{VIRL2_PASS}'
        username: '%ENV{VIRL2_USER}'
    os: linux
    type: linux
```
As it a virtual lab the credentials of each `node` will be set hardcoded to the new created `cmladmin` user:
```yaml
N9K-01:
    connections:
      a:
        command: open /ee9b21/n0/0
        protocol: telnet
        proxy: terminal_server
      defaults:
        class: unicon.Unicon
    credentials:
      default:
        password: cisco4ever!
        username: cmladmin
    os: nxos
    platform: n9k
    type: switch
```

The final pyATS testbed will be saved to the `inventory/` folder.
```
tree inventory
inventory
├── hosts.yaml
├── links.yaml
└── pyats_testbed_ee9b21.yaml
```

## How to use the Script

To run the script successfully, the three environment variables `VIRL2_URL`, `VIRL2_USER` and `VIRL2_PASS` which define the CML2 login credentials that the script will load.

```bash
export VIRL2_URL=x.x.x.x
export VIRL2_USER=admin
export VIRL2_PASS=xxxxxx
```

Both script execution options below can additionally be executed with the `--debug enable` argument to print more information to stdout.

### Option 1: Create a CML2 Lab with Nodes and Links only

Simply run the script with ```python3 cml2_lab_builder.py``` to create a CML2 lab from the `hosts.yaml` and the `links.yaml` file.

Example script output:
```
python3 cml2_lab_builder.py 

TASK [Initializing CML2 Server Connection]****************************************************

OK: [Loaded environment variable VIRL2_URL]
OK: [Loaded environment variable VIRL2_USER]
OK: [Loaded environment variable VIRL2_PASS]
SSL Verification disabled
OK: [10.128.16.51: Initialized CML2 server connection]
OK: [10.128.16.51: Created lab ID 63e86b]
OK: [10.128.16.51: Loaded file inventory/hosts.yaml]
OK: [10.128.16.51: Loaded file inventory/links.yaml]

TASK [Setup CML2 Lab ID 63e86b]***************************************************************

OK: [N9K-01: Created node]
OK: [N9K-02: Created node]
OK: [N9K-03: Created node]
OK: [N9K-01 <-> N9K-02: Created link l0 ]
OK: [N9K-01 <-> N9K-02: Created link l1 ]
OK: [N9K-01 <-> N9K-03: Created link l2 ]
OK: [N9K-01 <-> N9K-03: Created link l3 ]
OK: [N9K-02 <-> N9K-03: Created link l4 ]
OK: [N9K-02 <-> N9K-03: Created link l5 ]
OK: [N9K-01 <-> N9K-02: Added dynamic CML2 link details to dictionary]
OK: [N9K-01 <-> N9K-02: Added dynamic CML2 link details to dictionary]
OK: [N9K-01 <-> N9K-03: Added dynamic CML2 link details to dictionary]
OK: [N9K-01 <-> N9K-03: Added dynamic CML2 link details to dictionary]
OK: [N9K-02 <-> N9K-03: Added dynamic CML2 link details to dictionary]
OK: [N9K-02 <-> N9K-03: Added dynamic CML2 link details to dictionary]

TASK [Start CML2 Lab ID 63e86b]***************************************************************

Lab ID 63e86b is starting ... |████████████████████████████████████████| 0 in 3:16.4 (0.00/s)
OK: [10.128.16.51: Started CML2 lab Lab_ID_63e86b - ID 63e86b]

TASK [CML2 Lab Builder Recap]*****************************************************************

Total CML2 Lab Build Time: 3m 18s
Title: Lab_ID_63e86b         ID: 63e86b      URL: https://10.128.16.51/api/v0/labs/63e86b

Node: N9K-01                ID: n0          State: BOOTED      CPU: 64.28%
Node: N9K-02                ID: n1          State: BOOTED      CPU: 50.4%
Node: N9K-03                ID: n2          State: BOOTED      CPU: 53.55%
```

### Option 2: Create a CML2 Lab with Nodes, Links, Day 0 Configurations and a pyATS Testbed

Run the script with the argument `--day0 enable` to create a CML2 lab from the `hosts.yaml`, the `links.yaml`, and configuration files in the `config/` folder.

Example script output:
```
python3 cml2_lab_builder.py --day0 enable

TASK [Initializing CML2 Server Connection]****************************************************

OK: [Loaded environment variable VIRL2_URL]
OK: [Loaded environment variable VIRL2_USER]
OK: [Loaded environment variable VIRL2_PASS]
SSL Verification disabled
OK: [10.128.16.51: Initialized CML2 server connection]
OK: [10.128.16.51: Created lab ID ee9b21]
OK: [10.128.16.51: Loaded file inventory/hosts.yaml]
OK: [10.128.16.51: Loaded file inventory/links.yaml]

TASK [Setup CML2 Lab ID ee9b21]***************************************************************

OK: [N9K-01: Created node]
OK: [N9K-02: Created node]
OK: [N9K-03: Created node]
OK: [N9K-01 <-> N9K-02: Created link l0 ]
OK: [N9K-01 <-> N9K-02: Created link l1 ]
OK: [N9K-01 <-> N9K-03: Created link l2 ]
OK: [N9K-01 <-> N9K-03: Created link l3 ]
OK: [N9K-02 <-> N9K-03: Created link l4 ]
OK: [N9K-02 <-> N9K-03: Created link l5 ]
OK: [N9K-01 <-> N9K-02: Added dynamic CML2 link details to dictionary]
OK: [N9K-01 <-> N9K-02: Added dynamic CML2 link details to dictionary]
OK: [N9K-01 <-> N9K-03: Added dynamic CML2 link details to dictionary]
OK: [N9K-01 <-> N9K-03: Added dynamic CML2 link details to dictionary]
OK: [N9K-02 <-> N9K-03: Added dynamic CML2 link details to dictionary]
OK: [N9K-02 <-> N9K-03: Added dynamic CML2 link details to dictionary]

TASK [Prepare Day 0 Configuration for Lab ID ee9b21]******************************************

OK: [N9K-01: Start parsing config/N9K-01 configuration file]
OK: [N9K-01: Applied general day 0 configuration modifications]
OK: [N9K-01: Prepared all needed interfaces]
OK: [N9K-01: Deleted all not needed interfaces]
OK: [N9K-01: Modified all needed interfaces to match the dynamic CML2 interfaces]
OK: [N9K-01: Created temporary day 0 configuration file config/day0_N9K-01]


OK: [N9K-02: Start parsing config/N9K-02 configuration file]
OK: [N9K-02: Applied general day 0 configuration modifications]
OK: [N9K-02: Prepared all needed interfaces]
OK: [N9K-02: Deleted all not needed interfaces]
OK: [N9K-02: Modified all needed interfaces to match the dynamic CML2 interfaces]
OK: [N9K-02: Created temporary day 0 configuration file config/day0_N9K-02]


OK: [N9K-03: Start parsing config/N9K-03 configuration file]
OK: [N9K-03: Applied general day 0 configuration modifications]
OK: [N9K-03: Prepared all needed interfaces]
OK: [N9K-03: Deleted all not needed interfaces]
OK: [N9K-03: Modified all needed interfaces to match the dynamic CML2 interfaces]
OK: [N9K-03: Created temporary day 0 configuration file config/day0_N9K-03]



TASK [Apply Day 0 Configuration for Lab ID ee9b21]********************************************

OK: [N9K-01: Applied day 0 configuration to node]
OK: [N9K-01: Deleted temporary day 0 configuration file config/day0_N9K-01]


OK: [N9K-02: Applied day 0 configuration to node]
OK: [N9K-02: Deleted temporary day 0 configuration file config/day0_N9K-02]


OK: [N9K-03: Applied day 0 configuration to node]
OK: [N9K-03: Deleted temporary day 0 configuration file config/day0_N9K-03]



TASK [Start CML2 Lab ID ee9b21]***************************************************************

Lab ID ee9b21 is starting ... |████████████████████████████████████████| 0 in 3:56.9 (0.00/s)
OK: [10.128.16.51: Started CML2 lab Lab_ID_ee9b21 - ID ee9b21]

TASK [Initializing pyATS Testbed for Lab ID ee9b21]*******************************************

OK: [10.128.16.51: Generated temporary pyATS testbed on CML2 server]
OK: [10.128.16.51: Loaded temporary pyATS testbed for modifications]
OK: [10.128.16.51: Modified terminal server username and password]
OK: [10.128.16.51: Modified devices default credentials for the user cmladmin]
OK: [10.128.16.51: Saved final pyATS testbed inventory/pyats_testbed_ee9b21.yaml]
OK: [10.128.16.51: Deleted temporary pyATS testbed from filesystem]

TASK [Demo: pyATS on Nodes in Lab ID ee9b21]**************************************************

OK: [10.128.16.51: Loaded pyATS testbed inventory/pyats_testbed_ee9b21.yaml]


OK: [N9K-01: Extracted the device hostname and create an object]
OK: [N9K-01: Connected to the device]
OK: [N9K-01: Parsing output of show version into a dictionary]
OK: [N9K-01: Disconnected from the device]


OK: [N9K-02: Extracted the device hostname and create an object]
OK: [N9K-02: Connected to the device]
OK: [N9K-02: Parsing output of show version into a dictionary]
OK: [N9K-02: Disconnected from the device]


OK: [N9K-03: Extracted the device hostname and create an object]
OK: [N9K-03: Connected to the device]
OK: [N9K-03: Parsing output of show version into a dictionary]
OK: [N9K-03: Disconnected from the device]



TASK [CML2 Lab Builder Recap]*****************************************************************

Total CML2 Lab Build Time: 3m 59s
Total pyATS Automation Time: 0m 45s

Title: Lab_ID_ee9b21         ID: ee9b21      URL: https://10.128.16.51/api/v0/labs/ee9b21

Node: N9K-01                ID: n0          State: BOOTED      CPU: 15.24%
Node: N9K-02                ID: n1          State: BOOTED      CPU: 12.42%
Node: N9K-03                ID: n2          State: BOOTED      CPU: 15.2%
```

## Additional Information

The script was developed without only with static code analysis and functional testing.

## Open Points

* More testing
* Code refactoring
