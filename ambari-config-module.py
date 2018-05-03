#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Author: Mark Bittmann (https://github.com/mbittmann)
# Documentation section
DOCUMENTATION = '''
---
module: ambari_cluster_state
version_added: "1.0"
author: Mark Bittmann (https://github.com/mbittmann)
short_description: Create, delete, start or stop an ambari cluster
  - Create, delete, start or stop an ambari cluster
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
  config_tag:
    description:
      The tag version for a configuration type in Ambari
    required: no
  ignore_secrets:
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
  - name: Create a 
    ambari_cluster_state:
        host: localhost
        port: 8080
        username: admin
        password: admin
        cluster_name: my_cluster
        config_type: config_type_a
        config_tag: version1372818
        ignore_secrets: true
        config_map:
          - name: key x
            value: value y
'''
__author__ = 'timqin'
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
    import time
except ImportError:
    TIME_FOUND = False
else:
    TIME_FOUND = True


def main():

    argument_spec = dict(
        host=dict(type='str', default=None, required=True),
        port=dict(type='int', default=None, required=True),
        username=dict(type='str', default=None, required=True),
        password=dict(type='str', default=None, required=True),
        cluster_name=dict(type='str', default=None, required=True),
        config_type=dict(type='str', default=None, required=True),
        config_tag=dict(type='str', required=False, required=False),
        ignore_secret = dict(default=True, required=False, choices=BOOLEANS)
        config_map=dict(type='list', default=[], required=True)
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

    if not TIME_FOUND:
        module.fail_json(
            msg='time library is required for this module')

    p = module.params

    host = p.get('host')
    port = p.get('port')
    username = p.get('password')
    password = p.get('password')
    cluster_name = p.get('cluster_name')
    config_type = p.get('config_type')
    config_tag = p.get('config_tag')
    config_map = p.get('config_map')

    ambari_url = 'http://{0}:{1}'.format(host, port)

    try:
        if config_tag is None:
            config_index = get_cluster_config_index(ambari_url, username, password, cluster_name)
            config_tag = config_index[config_type]["tag"]
        cluster_config = get_cluster_config(ambari_url, username, password, cluster_name, config_type, config_tag)
        changed = False
        result_map = {}
        for key in cluster_config:
            current_value = cluster_config[key]
            if key in config_map:
                desired_value = config_map[key]
                if current_value == desired_value:
                    # if value matched, do nothing
                    continue
                else:
                    if current_value.startswith('SECRET'):
                        # update state base on ignore secret or not
                        if ignore_secret:
                            changed = False
                        else:
                            changed = True
                    result_map[key] = get_config_desired_value(current_map, key, desired_value, 'str')
            else:
                result_map[key] = current_value
        if changed:
            request = update_cluster_config(ambari_url, username, password, cluster_name, config_type, result_map)
            module.exit_json(changed=True, results=request.content)
        else:
            module.exit_json(changed=False, msg='No changes in config')
    except requests.ConnectionError as e:
        module.fail_json(msg="Could not connect to Ambari client: " + str(e.message))
    except AssertionError as e:
        module.fail_json(msg=e.message)
    except Exception as e:
        module.fail_json(msg="Ambari client exception occurred: " + str(e.message))


def get_config_desired_value(current_map, key, desired_value, mode):
    if mode == 'str':
        return desired_value
    elif mode == 'xml':
        return desired_value
    else:
        return desired_value



def update_cluster_config(ambari_url, user, password, cluster_name, config_type, updated_map):
    ts = time.time()
    tag_ts = ts * 1000
    payload = {
        'type': config_type, 
        'tag': 'version{0}'.format('%d' % tag_ts),
        'properties': updated_map,
        'service_config_version_note': 'Ansible module syncing',
        }
    put_body = {'Clusters': {'desired_config':[]}}
    put_body['Clusters']['desired_config'].append(payload)
    r = put(ambari_url, user, password, '/api/v1/clusters/{0}',json.dumps(put_body))
    try:
        assert r.status_code == 200 or r.status_code == 201
    except AssertionError as e:
        e.message = 'Coud not update cluster with desired configuration: request code {0}, \
                    request message {1}'.format(r.status_code, r.content)
        raise
    return r


def get_cluster_config_index(ambari_url, user, password, cluster_name):
    r = get(ambari_url, user, password, '/api/v1/clusters/{0}?fields=Clusters/desired_configs'.format(cluster_name))
    try:
        assert r.status_code == 200
    except AssertionError as e:
        e.message = 'Coud not get cluster desired configuration: request code {0}, \
                    request message {1}'.format(r.status_code, r.content)
        raise
    clusters = json.loads(r.content)
    return clusters['Clusters']['desired_configs']


def get_cluster_config(ambari_url, user, password, cluster_name, config_type, config_tag):
    r = get(ambari_url, user, password, '/api/v1/clusters/{0}/configurations\?type={1}&tag={2}'.format(cluster_name, config_type, config_tag))
    try:
        assert r.status_code == 200
    except AssertionError as e:
        e.message = 'Coud not get cluster configuration: request code {0}, \
                    request message {1}'.format(r.status_code, r.content)
        raise
    config = json.loads(r.content)
    return config['items'][0]['properties']


def get(ambari_url, user, password, path):
    headers = {'X-Requested-By': 'ambari'}
    r = requests.get(ambari_url + path, auth=(user, password), headers=headers)
    return r


def put(ambari_url, user, password, path, data):
    headers = {'X-Requested-By': 'ambari'}
    r = requests.put(ambari_url + path, data=data, auth=(user, password), headers=headers)
    return r


def post(ambari_url, user, password, path, data):
    headers = {'X-Requested-By': 'ambari'}
    r = requests.post(ambari_url + path, data=data, auth=(user, password), headers=headers)
    return r




if __name__ == '__main__':
    main()