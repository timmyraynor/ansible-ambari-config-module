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
  protocol:
    description:
      The protocol for the ambari web server (http / https)
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
# If you are aiming to provide a full file replacement / template replacement, please use the `lookup` plugin provided
# in native ansible

# example:

  - name: Update a cluster configuration
    ambari_cluster_config:
        protocol: http
        host: localhost
        port: 8080
        username: admin
        password: admin
        cluster_name: my_cluster
        config_type: admin-properties
        ignore_secret: true
        timeout_sec: 10
        config_map:
          db_root_user:
            value: root
          key_x2:
            value: value_y2
            regex: ^your_regex to fully replace
          key_x3:
            value: "{{lookup('template', './files/mytemplate.j2')}}"
'''

from ansible.module_utils.basic import AnsibleModule
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

try:
    import re
except ImportError:
    REGEX_FOUND = False
else:
    REGEX_FOUND = True

import traceback


def main():

    argument_spec = dict(
        protocol=dict(type='str', default='http', required=False),
        host=dict(type='str', default=None, required=True),
        port=dict(type='int', default=None, required=True),
        username=dict(type='str', default=None, required=True),
        password=dict(type='str', default=None, required=True, no_log=True),
        cluster_name=dict(type='str', default=None, required=True),
        config_type=dict(type='str', default=None, required=True),
        config_tag=dict(type='str', default=None, required=False),
        ignore_secret=dict(default=True, required=False,
                           choices=[True, False]),
        timeout_sec=dict(type='int', default=10, required=False),
        config_map=dict(type='dict', default=None, required=True)
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

    if not REGEX_FOUND:
        module.fail_json(
            msg='regex(re) library is required for this module')

    p = module.params

    protocol = p.get('protocol')
    host = p.get('host')
    port = p.get('port')
    username = p.get('username')
    password = p.get('password')
    cluster_name = p.get('cluster_name')
    config_type = p.get('config_type')
    config_tag = p.get('config_tag')
    config_map = p.get('config_map')
    ignore_secret = p.get('ignore_secret')
    connection_timeout = p.get('timeout_sec')

    process_ambari_config(module, protocol, host, port, username, password,
                          cluster_name, config_type, config_tag, config_map, ignore_secret, connection_timeout)


def process_ambari_config(module, protocol, host, port, username, password, cluster_name, config_type, config_tag, config_map, ignore_secret, connection_timeout):
    ambari_url = '{0}://{1}:{2}'.format(protocol, host, port)

    try:
        # Get current effective version/tag if not specified
        if config_tag is None:
            config_index = get_cluster_config_index(
                ambari_url, username, password, cluster_name, connection_timeout)
            config_tag = config_index[config_type]["tag"]
        # Get config using the effective tag
        overall_cluster_config = get_cluster_config(
            ambari_url, username, password, cluster_name, config_type, config_tag, connection_timeout)
        cluster_config = overall_cluster_config['properties']
        
        changed, has_secrets, result_map, updated_map = sync_config_map_with_cluster(cluster_config, config_map, ignore_secret)

        if changed:
            request = update_cluster_config(
                ambari_url, username, password, cluster_name, config_type, result_map, extract_properties_attributes(overall_cluster_config), connection_timeout)
            module.exit_json(
                changed=True, results=request.content, msg={'result': result_map, 'updates': updated_map})
        else:
            if has_secrets:
                request = update_cluster_config(ambari_url, username, password, cluster_name,
                                                config_type, result_map, extract_properties_attributes(overall_cluster_config), connection_timeout)
                module.exit_json(
                    changed=False, results=request.content, msg={'result': result_map, 'updates': updated_map})
            else:
                module.exit_json(changed=False, msg='No changes in config')
    except requests.ConnectionError as e:
        module.fail_json(
            msg="Could not connect to Ambari client: " + str(e.message), stacktrace=traceback.format_exc())
    except AssertionError as e:
        module.fail_json(msg=e.message, stacktrace=traceback.format_exc())
    except Exception as e:
        module.fail_json(
            msg="Ambari client exception occurred: " + str(e.message), stacktrace=traceback.format_exc())


def sync_config_map_with_cluster(cluster_config, config_map, ignore_secret):
    changed = False
    has_secrets = False
    result_map = {}
    updated_map = {}
    # Start iterate through the config with input
    for key in cluster_config:
        current_value = cluster_config[key]
        if key in config_map:
            desired_value = config_map[key].get('value')
            if desired_value is not None and (current_value == desired_value or str(current_value).lower() == str(desired_value).lower()):
                # if value matched, put it directly into the map
                result_map[key] = current_value
            else:
                # Mismatched!
                # Get the require-to-update value base on regex/non-regex
                (actual_value, updated) = get_config_desired_value(
                    cluster_config, key, desired_value, config_map[key].get('regex'))
                # base on the regex sub, if not changed then change the change state to False
                if ignore_secret and current_value.startswith('SECRET'):
                    updated = False
                    has_secrets = True
                changed = changed or updated
                result_map[key] = actual_value
                if updated:
                    if 'password' in key or 'pw' in key or 'token' in key:
                        updated_map[key] = {'origin': hash_passwords(
                            cluster_config[key]), 'changed_to': hash_passwords(actual_value)}
                    else:
                        updated_map[key] = {
                            'origin': cluster_config[key], 'changed_to': actual_value}
        else:
            result_map[key] = current_value

    # Loop through all config_map and make sure additional keys are put into the map as well
    for key in config_map:
        if key not in cluster_config:
            changed = True
            result_map[key] = config_map.get(key).get('value')
            updated_map[key] = {
                'origin': 'no such key', 'changed_to': config_map.get(key).get('value')
            }

    return changed, has_secrets, result_map, updated_map


def hash_passwords(pw):
    return '*' * len(pw)


def get_config_desired_value(current_map, key, desired_value, regex):
    if regex is None or regex == '':
        # if not contains regex, straight return the desired_value
        return desired_value, True
    else:
        # if contains regex, us re.sub to replace the regex pattern with desired_value
        result = re.sub(regex, desired_value, current_map[key])
        return result, result == current_map[key]


def update_cluster_config(ambari_url, user, password, cluster_name, config_type, updated_map, properties_attributes, connection_timeout):
    ts = time.time()
    tag_ts = ts * 1000
    payload = {
        'type': config_type,
        'tag': 'version{0}'.format('%d' % tag_ts),
        'properties': updated_map,
        'service_config_version_note': 'Ansible module syncing',
    }
    if properties_attributes is not None:
        payload['properties_attributes'] = properties_attributes
    put_body = {'Clusters': {'desired_config': []}}
    put_body['Clusters']['desired_config'].append(payload)
    put_list = []
    put_list.append(put_body)
    r = put(ambari_url, user, password,
            '/api/v1/clusters/{0}'.format(cluster_name), json.dumps(put_list), connection_timeout)
    try:
        assert r.status_code == 200 or r.status_code == 201
    except AssertionError as e:
        e.message = 'Coud not update cluster with desired configuration: request code {0}, \
                    request message {1}'.format(r.status_code, r.content)
        raise
    return r


def extract_properties_attributes(overall_config):
    try:
        properties_attribute = overall_config['properties_attributes']
        return properties_attribute
    except KeyError:
        properties_attribute = None
        return properties_attribute


def get_cluster_config_index(ambari_url, user, password, cluster_name, connection_timeout):
    r = get(ambari_url, user, password,
            '/api/v1/clusters/{0}?fields=Clusters/desired_configs'.format(cluster_name), connection_timeout)
    try:
        assert r.status_code == 200
    except AssertionError as e:
        e.message = 'Coud not get cluster desired configuration: request code {0}, \
                    request message {1}'.format(r.status_code, r.content)
        raise
    clusters = json.loads(r.content)
    return clusters['Clusters']['desired_configs']


def get_cluster_config(ambari_url, user, password, cluster_name, config_type, config_tag, connection_timeout):
    r = get(ambari_url, user, password,
            '/api/v1/clusters/{0}/configurations?type={1}&tag={2}'.format(cluster_name, config_type, config_tag), connection_timeout)
    try:
        assert r.status_code == 200
    except AssertionError as e:
        e.message = 'Coud not get cluster configuration: request code {0}, \
                    request message {1}'.format(r.status_code, r.content)
        raise
    config = json.loads(r.content)
    try:
        assert config['items'][0]['properties'] is not None
        return config['items'][0]
    except KeyError as e:
        e.message = 'Could not find the right properties key, request code {0}, \
                     possiblly having a wrong tag, response content is: {1}'.format(r.status_code, r.content)
        raise
    except AssertionError as e:
        e.message = 'Could not find the right properties key, request code {0}, \
                     possiblly having a wrong tag, response content is: {1}'.format(r.status_code, r.content)
        raise


def get(ambari_url, user, password, path, connection_timeout):
    headers = {'X-Requested-By': 'ambari'}
    r = requests.get(ambari_url + path, auth=(user, password),
                     headers=headers, timeout=connection_timeout)
    return r


def put(ambari_url, user, password, path, data, connection_timeout):
    headers = {'X-Requested-By': 'ambari'}
    r = requests.put(ambari_url + path, data=data,
                     auth=(user, password), headers=headers, timeout=connection_timeout)
    return r


if __name__ == '__main__':
    main()
