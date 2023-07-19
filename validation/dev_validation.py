#/bin/python
from netmiko import Netmiko
import yaml
import sys
import difflib

from pyats.topology import loader
from virl2_client import ClientLibrary

###Cisco CML credentials
cml_host = 'https://10.10.20.161'
cml_user = 'developer'
cml_pass = 'C1sco12345'
cml_dev_lab = 'dev-network'

### Get devices hostname passed through CICD environment variables, use pyATS to log into the console for each device, get the show running-config and store output into a .txt file
env_list = sys.argv[1].split(',')
client = ClientLibrary(cml_host, cml_user, cml_pass, ssl_verify=False)
lab_id = client.find_labs_by_title(cml_dev_lab)
lab_name = client.join_existing_lab(lab_id[0].id)
testbed_yaml = lab_name.get_pyats_testbed()
testbed = loader.load(testbed_yaml)
testbed.devices.terminal_server.credentials.update({'default': {'username': cml_user, 'password': cml_pass}})
for device in env_list:
  conn = testbed.devices[device]
  conn.connect()
  command_out = conn.execute('show run')
  output_file = open(device+'_dev.txt','a')
  output_file.write("#"*25+"\n")
  output_file.write("#"*10+" DEV "+"#"*10+"\n")
  output_file.write("#"*25+"\n")
  output_file.write(command_out)
  output_file.close()

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
  open_file = open(conn_device['hostname']+"_prod.txt", 'a')
  open_file.write("#"*25+"\n")
  open_file.write("#"*10+" PRD "+"#"*10+"\n")
  open_file.write("#"*25+"\n")
  open_file.write(output_prod)
  open_file.close()



###Loop through the env_list, open the files taken from production and dev, compare them and generate HTML file
for device in env_list:
  open_file_dev = open(device+"_dev.txt").readlines()
  open_file_prod = open(device+"_prod.txt").readlines()
  diff = difflib.ndiff(open_file_prod,open_file_dev)
  diff_html = difflib.HtmlDiff(wrapcolumn=80).make_file(open_file_prod, open_file_dev)
  open_diff_file = open(device+"_compare.html", 'w')
  open_diff_file.write(diff_html)
