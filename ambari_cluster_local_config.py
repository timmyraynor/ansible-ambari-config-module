#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Documentation section
DOCUMENTATION = '''
---
module: ambari_cluster_config
version_added: "1.0"
short_description: Capture or update Ambari cluster configurations
  - Capture or update Ambari cluster configurations
options:
  host:
    description:
      The hostname for the ambari web server
  port:
    description:
      The port for the ambari web server
  username:
    description:
      The username for the ambari web server
  password:
    description:
      The name of the cluster in web server
    required: yes
  cluster_name:
    description:
      The name of the cluster in ambari
    required: yes
  config_type:
    description:
      The configuration type for Ambari cluster configurations
    required: yes
  tag:
    description:
      The tag version for a configuration type in Ambari
    required: no
  ignore_secret:
    description:
      Whether to ignore the secrets as the configurations of Ambari secrets is not shown via api calls, Default is True
    required: no
  config_map:
    description:
      The map object for all configurations need to be checked and updated
    required: yes
'''

EXAMPLES = '''
# must use full relative path to any files in stored in roles/role_name/files/

# NOT SUPPORT list:
  - Don't support any config that is not within Ambari config, so if the config file does not have a particular key
  you cannot add it.

# example:

  - name: Update a cluster configuration
    ambari_cluster_config:
        host: localhost
        port: 8080
        username: admin
        password: admin
        cluster_name: my_cluster
        config_type: admin-properties
        config_key: db_root_user
        config_value: root
        config_file_loc: /var/lib/ambari-server/resources/scripts/configs.sh
'''
from ansible.module_utils.basic import *
import json
import os
try:
    import requests
except ImportError:
    REQUESTS_FOUND = False
else:
    REQUESTS_FOUND = True

try:
    import yaml
except ImportError:
    YAML_FOUND = False
else:
    YAML_FOUND = True

try:
    import re
except ImportError:
    REGEX_FOUND = False
else:
    REGEX_FOUND = True

try:
    import subprocess
except ImportError:
    SUBPROC_FOUND = False
else:
    SUBPROC_FOUND = True


def main():

    argument_spec = dict(
        host=dict(type='str', default=None, required=True),
        port=dict(type='int', default=None, required=True),
        username=dict(type='str', default=None, required=True),
        password=dict(type='str', default=None, required=True, no_log=True),
        cluster_name=dict(type='str', default=None, required=True),
        config_type=dict(type='str', default=None, required=True),
        config_key=dict(type='str', default=None, required=True),
        config_value=dict(type='str', default=None, required=True),
        config_file_loc=dict(
            type='str', default='/var/lib/ambari-server/resources/scripts/configs.sh', required=None)
    )

    module = AnsibleModule(
        argument_spec=argument_spec
    )

    if not REQUESTS_FOUND:
        module.fail_json(
            msg='requests library is required for this module')

    if not YAML_FOUND:
        module.fail_json(
            msg='pyYaml library is required for this module')

    if not REGEX_FOUND:
        module.fail_json(
            msg='regex(re) library is required for this module')

    if not SUBPROC_FOUND:
        module.fail_json(
            msg='subprocess library is required for this module')

    p = module.params

    host = p.get('host')
    port = p.get('port')
    username = p.get('username')
    password = p.get('password')
    cluster_name = p.get('cluster_name')
    config_type = p.get('config_type')
    config_key = p.get('config_key')
    config_value = p.get('config_value')
    config_file_loc = p.get('config_file_loc')

    try:
        output, has_changed = update_cluster_config(config_file_loc,
                                                    host, username, password, port, cluster_name, config_type, config_key, config_value)

        module.exit_json(changed=has_changed, results=output)
    except requests.ConnectionError as e:
        module.fail_json(
            msg="Could not connect to Ambari client: " + str(e.message))
    except AssertionError as e:
        module.fail_json(msg=e.message)
    except Exception as e:
        module.fail_json(
            msg="Ambari client exception occurred: " + str(e.message))


def update_cluster_config(config_file_loc, host, user, password, port, cluster_name, config_type, key, value):
    content_output = subprocess.check_output([config_file_loc, '-u', user, '-p', password,
                                              '-port', port, 'set', host, cluster_name, config_type, key, value])
    return parse_update_cluster_response(content_output)


def parse_update_cluster_response(response):
    matched = re.search(
        r"########## Performing 'set'.*Tag:(.*)\)", response)
    previous_version = matched.group(1)

    matched2 = re.search(
        r'########## NEW Site\:.*Tag:(.*)', response)
    current_version = matched2.group(1)
    return response, previous_version != current_version


if __name__ == '__main__':
    main()
