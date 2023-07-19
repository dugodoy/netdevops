#/bin/python
from netmiko import Netmiko
import yaml
import sys
import difflib

### Get devices hostname passed through CICD environment variables, use pyATS to log into the console for each device, get the show running-config and store output into a .txt file
env_list = sys.argv[1].split(',')

### Load ansible inventory file
inventory_file = open('inventory/hosts.yml')
inventory = yaml.safe_load(inventory_file)

###Loop through the ansible inventory file and get device ip, username, password and network_os
device_list=[]
device_groups = inventory['all']['children']
for group in device_groups:
  for device in device_groups[group]['hosts']:
    if device in env_list:
      dict_devices = {'ip': device_groups[group]['hosts'][device]['ansible_host'],
                      'username': device_groups[group]['hosts'][device]['ansible_user'],
                      'password': device_groups[group]['hosts'][device]['ansible_password'],
                      'global_delay_factor':3,
                      'hostname': device,
                      'network_os': device_groups[group]['hosts'][device]['ansible_network_os']}
      device_list.append(dict_devices)

###Connect to the production devices, take show running-config and store in a .txt file
for conn_device in device_list:
  if conn_device['network_os'] == 'nxos':
    conn_device['device_type'] = 'cisco_nxos'
  if conn_device['network_os'] == 'ios':
    conn_device['device_type'] = 'cisco_ios'
  hostname = conn_device['hostname']
  network_os = conn_device['network_os']
  conn_device.pop('hostname')
  conn_device.pop('network_os')
  net_connect = Netmiko(**conn_device)
  output_prod = net_connect.send_command("show running-config")
  net_connect.disconnect()
  conn_device['hostname'] = hostname
  conn_device['network_os'] = network_os
  open_file = open(conn_device['hostname']+"_prod.txt", 'w')
  open_file.write(output_prod)
  open_file.close()

