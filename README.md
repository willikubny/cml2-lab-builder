# CML2 Lab Builder

[![published](https://static.production.devnetcloud.com/codeexchange/assets/images/devnet-published.svg)](https://developer.cisco.com/codeexchange/github/repo/willikubny/cml2_lab_builder)

The script helps to automate the initial CML2 lab building process by creating the topology with all its nodes and links. Optional the script can apply the day0 configuration to each node before the nodes get started. Another optional feature is to create an OOB network VRF with external connection in bridge mode, to access the lab nodes by IP from outside. The details regarding the OOB network are described later.
When the script is executed with the day0 or the OOB argument, then also a pyATS testbed will be created after all CML2 nodes are booted. There are several modifications for the day0 configuration and the pyATS testbed which the script does. These modifications are described later.
For all script execution option the debug argument can be enabled to print additional information to stout.

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
usage: cml2_lab_builder.py [-h] [--day0 DAY0] [--oob OOB] [--debug DEBUG]

Creates a CML2 lab from a hosts.yaml and a links.yaml. Optional creates a OOB network from a oob.yaml file and applies day 0
device configurations files.

optional arguments:
  -h, --help     show this help message and exit
  --day0 DAY0    Optional: Enable day 0 configuration
  --oob OOB      Optional: Create an OOB VRF with external connection
  --debug DEBUG  Optional: Enable stdout debug print
```

The script needs a `inventory/hosts.yaml` and a `inventory/links.yaml` file to build the CML2 lab topology. If a day 0 configuration should be applied, then the configuration files for each node needs to be present in the `config/` folder. The `inventory/oob.yaml` file is optional and specifies the OOB network details when the script is executed with the OOB argument.

The repository has an example topology with its `hosts.yaml`, `links.yaml`, `oob.yaml` and the three configuration files `N9K-01`, `N9K-02` and `N9K-03` for the nodes.

```
tree

# Output
.
├── LICENSE
├── Makefile
├── README.md
├── cml2_lab_builder.py
├── config
│   ├── N9K-01
│   ├── N9K-02
│   └── N9K-03
├── inventory
│   ├── hosts.yaml
│   ├── links.yaml
│   └── oob.yaml
└── requirements.txt
```

## Makefile

The `Makefile` is used to run the `black` auto-formatter, `pylint` linting and the execution of `bandit`.
All `pylint` warnings that should be ignored are part of the script with a `pylint` control message e.g `# pylint: disable=xyz`.

```make
# 'make' by itself runs the 'all' target
.DEFAULT_GOAL := all

.PHONY: all
all:	format lint

.PHONY: format
format:
	@echo "[Task] Starting format *********************************************"
	find . -name "*.py" | xargs black --diff
	find . -name "*.py" | xargs black

.PHONY: lint
lint:
	@echo "[Task] Starting yamllint *******************************************"
	find . -name "*.yaml" | xargs yamllint
	@echo "[Task] Starting pylint *********************************************"
	find . -name "*.py" | xargs pylint
	@echo "[Task] Starting bandit *********************************************"
	find . -name "*.py" | xargs bandit
```

## Creating the Topology Files

When writing the `hosts.yaml` and `links.yaml` files, its important the the hostname are identical in each file. Otherwise the script will fail. The interfaces in the `links.yaml` file are only needed if the also a day 0 configuration should be applied. The interface value needs to match the interface in the provided configuration file. If no day 0 configuration is needed, the interface value can be blank.

Node definitions in the `inventory/hosts.yaml` file:
```yaml
---
# For CML2 only the data dictionary with cml_label, cml_platform
# and cml_position under the hostname is required.
#
# The following is an inventory example to extend a nornir host
# file with the information needed by the cml2_lab_build script.
#
# NXOS-SW-1:
#  hostname: 10.10.100.11
#  username: cisco
#  password: cisco
#  connection_options:
#    netmiko:
#      platform: cisco_nxos_ssh
#    napalm:
#      platform: nxos_ssh
#    netconf:
#      extras:
#        allow_agent: False
#        hostkey_verify: False
#        look_for_keys: False
#  data:
#     cml_label: SW-1
#     cml_platform: iosvl2
#     cml_position: [0, -100]

N9K-01:
  data:
    cml_label: N9K-01
    cml_platform: nxosv9000
    cml_position: [-300, 0]

N9K-02:
  data:
    cml_label: N9K-02
    cml_platform: nxosv9000
    cml_position: [0, -150]

N9K-03:
  data:
    cml_label: N9K-03
    cml_platform: nxosv9000
    cml_position: [0, 150]
```

Link definitions in the `links.yaml` file:
```yaml
---
# host_a and host_b are the CML2 nodes where a link will be created.
# interface_a and interface_b needs to match exactly with the provided
# config file, as the script will take these interfaces configurations
# and configure the dynamically assigned interfaces by CML2.
# If no configuration is provided, the values of these keys can be blank.
#
# For example:
# - host_a: Hostname-A
#    interface_a: GigabitEthernet1/0/1
#    host_b: Hostname-B
#    interface_b: GigabitEthernet1/0/1
# or
# - host_a: Hostname-A
#    interface_a:
#    host_b: Hostname-B
#    interface_b:

link_list:
  - host_a: N9K-01
    interface_a: Ethernet1/53
    host_b: N9K-02
    interface_b: Ethernet1/51

  - host_a: N9K-01
    interface_a: Ethernet1/54
    host_b: N9K-02
    interface_b: Ethernet1/52

  - host_a: N9K-01
    interface_a: Ethernet1/51
    host_b: N9K-03
    interface_b: Ethernet1/53
```

OOB network definition in the `oob.yaml` file:
```yaml
---
# OOB network configuration file.
# The oob_vlan_number needs to be an integer. The oob_vlan_subnet needs
# to be the subnet with the mask as /xx and the oob_vlan_gateway needs
# to be an ip-address within this range.
#
# For example:
# oob_vlan_number: 100
# oob_vlan_subnet: 10.10.100.0/24
# oob_vlan_gateway: 10.10.100.1

oob_vlan_number: 100
oob_vlan_subnet: 10.10.100.0/24
oob_vlan_gateway: 10.10.100.1
```

## Applying Day0 Configuration Files

When day0 configuration files should be applied, the filename needs to match the nodes hostname. No modifications should be needed to the configurations files, as the script will know which interfaces are needed for the lab based on the details from the `links.yaml` file. The script will delete all not needed physical port configurations. Further a additional user named `cmladmin` will be created to simplify the pyATS testbed creation.

The day0 interface configuration modifications were tested mostly with the following node definitions:
* iosv
* iosvl2
* nxosv
* nxosv9000

## OOB Network

When the script is executed with the OOB argument enabled, an OOB network within a additional VRF will be created and the first interface of each node will be part of the OOB network. An external connector with an unmanaged switch in front will be created and the first interface of each node will be connected to this unmanaged switch. With the details from the `oob.yaml` file the OOB VLAN, subnet and default-gateway are specified to configure each node with the needed configuration. The script starts the ip-address assignment with the first ip-address of the subnet and therefor assumes that all ip-addresses exept the default-gateway are free.

The OOB network is implemented for the following node definitions:
* nxosv9000
* nxosv
* iosvl2
* iosv
* csr1000v
* iosxrv
* iosxrv9000

If the lab topology contains node definitions which are not supported for the OOB network, then no link from these nodes to the OOB network will be created. At the end of the script a `show interface brief` with pyATS is printed to the stout to verify that all OOB interfaces are up. Also a ip-address assignment summary will be printed to stout in the recap section at the end.

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

All script execution options below can additionally be executed with the `--debug enable` argument to print more information to stdout.

###
#### Option 1: Create a CML2 Lab Topology with Nodes and Links only

Simply run the script with ```python3 cml2_lab_builder.py``` to create a CML2 lab topology from the `hosts.yaml` and the `links.yaml` file.

###
#### Option 2: Create a CML2 Lab Topology with Day0 Configurations and a pyATS Testbed

Run the script with the argument `--day0 enable` to create a CML2 lab from the `hosts.yaml`, the `links.yaml`, and configuration files in the `config/` folder.

###
#### Option 3: Create a CML2 Lab Topology with an OOB network with external access in bridge mode and a pyATS Testbed

Run the script with the argument `--oob enable` to create a CML2 lab from the `hosts.yaml`, the `links.yaml` and the `oob.yaml` file.

###
#### Option 2 and 3 together: Create a CML2 Lab Topology with Day0 Configurations, an OOB network with external access in bridge mode and a pyATS Testbed

Run the script with the argument `--day0 enable` and `--oob enable` to create a CML2 lab from the `hosts.yaml`, the `links.yaml`, the `oob.yaml` and configuration files in the `config/` folder.

## Additional Information

The script was developed with static code analysis, black auto-formatting and functional testing.

## Open Points

* More extensive testing
* Code refactoring of the main function
