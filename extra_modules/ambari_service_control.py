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
  state:
    description:
      The configuration type for Ambari cluster configurations
    required: yes
'''

EXAMPLES = '''
# If you are aiming to provide a full file replacement / template replacement, please use the `lookup` plugin provided
# in native ansible

# NOT SUPPORT list:
  - Don't support any config that is not within Ambari config, so if the config file does not have a particular key
  you cannot add it.

# example:

  - name: Update a cluster configuration
    ambari_service_control:
        host: localhost
        port: 8080
        username: admin
        password: admin
        cluster_name: my_cluster
        service: HDFS
        state: STARTED
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

import time
import traceback


def main():

    argument_spec = dict(
        host=dict(type='str', default=None, required=True),
        port=dict(type='int', default=None, required=True),
        username=dict(type='str', default=None, required=True),
        password=dict(type='str', default=None, required=True, no_log=True),
        cluster_name=dict(type='str', default=None, required=True),
        service=dict(type='str', default=None, required=True),
        state=dict(type='str', default=None, required=True,
                   choices=['started', 'installed']),
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

    p = module.params

    host = p.get('host')
    port = p.get('port')
    username = p.get('username')
    password = p.get('password')
    cluster_name = p.get('cluster_name')
    service_name = p.get('service')
    state = p.get('state')

    ambari_url = 'http://{0}:{1}'.format(host, port)
    services_fact = get_all_services_states(
        ambari_url, username, password, cluster_name)

    try:
        if service_name.lower() == 'all':
            # start/stop all services
            process_all_services(ambari_url, username, password,
                                module, cluster_name, state)
        else:
            # process individual services
            services_fact = get_all_services_states(
                ambari_url, username, password, cluster_name)
            process_individual_service(
                services_fact, ambari_url, username, password, module, cluster_name, service_name, state)
    except requests.ConnectionError as e:
        module.fail_json(
            msg="Could not connect to Ambari client: " + str(e.message), stacktrace=traceback.format_exc())
    except AssertionError as e:
        module.fail_json(msg=e.message, stacktrace=traceback.format_exc())
    except Exception as e:
        module.fail_json(
            msg="Ambari client exception occurred: " + str(e.message), stacktrace=traceback.format_exc())


def process_all_services(ambari_url, username, password, module, cluster_name, state):
    if state == 'started':
        context_info = 'START'
    else:
        context_info = 'STOP'
    payload = {
        'RequestInfo': {
            'context': '_PARSE_.{0}.ALL_SERVICES'.format(context_info),
            'operation_level': {
                'level': 'CLUSTER',
                'cluster_name': cluster_name
            }
        },
        'Body': {
            'ServiceInfo':  {
                'state': state.upper()
            }
        }
    }
    r = put(ambari_url, username, password, '/api/v1/clusters/{0}/services'.format(
        cluster_name), json.dumps(payload))
    progress, _ = process_ambari_request_response(
        r, cluster_name, ambari_url, username, password)
    module.exit_json(changed=True, results=r.content,
                     request_status=json.dumps(progress))


def process_individual_service(services_fact, ambari_url, username, password, module, cluster_name, service_name, state):
    for service_state in services_fact:
        s_name = service_state.get('ServiceInfo').get('service_name')
        s_state = service_state.get('ServiceInfo').get('state')

        if str(service_name).lower() == str(s_name).lower():
            if s_state.lower is not None and state.lower() == s_state.lower():
                module.exit_json(
                    changed=False, msg='No changes in service state')
            else:
                # Update state base on the service/state specified
                r, progress = update_service_state(
                    cluster_name, s_name, state, ambari_url, username, password)
                module.exit_json(changed=True, results=r.content,
                                 request_status=json.dumps(progress))


def update_service_state(cluster, service_name, state, ambari_url, username, password):
    payload = {
        'RequestInfo': {
            'context': '{0} {1} Service in Cluster[{2}] via API'.format(state, service_name, cluster)
        },
        'Body': {
            'ServiceInfo':  {
                'state': state.upper()
            }
        }
    }
    r = put(ambari_url, username, password, '/api/v1/clusters/{0}/services/{1}'.format(
        cluster, service_name.upper()), json.dumps(payload))
    progress, _ = process_ambari_request_response(
        r, cluster, ambari_url, username, password)
    return r, progress


def process_ambari_request_response(r, cluster_name, ambari_url, user, password):
    try:
        assert r.status_code == 200 or r.status_code == 201 or r.status_code == 202
    except AssertionError as e:
        e.message = 'Coud not process response as: request code {0}, \
                    request message {1}'.format(r.status_code, r.content)
        raise

    response = json.loads(r.content)
    request_meta = response.get('Requests')

    try:
        request_status = request_meta.get('status')
        assert request_status.upper() == 'ACCEPTED' or request_status.upper() == 'COMPLETED'
    except AssertionError as e:
        e.messge = 'Request sent to ambari server is not accepted or completed. request code: {0}, messge: {1}'.format(
            r.status_code, r.content)
        raise

    retry_counter = 0
    while True and retry_counter < 10:
        progress, completed = wait_for_request_bounded(
            cluster_name, ambari_url, user, password, request_meta)
        if completed:
            return progress, completed
        else:
            time.sleep(10)
            retry_counter = retry_counter + 1

    raise Exception('Max request waiting retries')


def wait_for_request_bounded(cluster_name, ambari_url, user, password, request_meta):
    res = get(ambari_url, user, password,
              '/api/v1/clusters/{0}/requests/{1}'.format(cluster_name, request_meta.get('id')))
    try:
        assert res.status_code == 200 or res.status_code == 201
    except AssertionError as e:
        e.message = 'Coud not obtain requests status: request code {0}, \
                    request message {1}'.format(res.status_code, res.content)
        raise
    progress = json.loads(res.content)
    try:
        assert progress.get('Requests').get(
            'request_status').upper() != 'FAILED'
    except AssertionError as e:
        e.messge = 'Request has failed due to: {0}'.format(res.content)
        raise
    if progress.get('Requests').get('request_status').upper() == 'COMPLETED':
        return progress, True
    else:
        return progress, False


def get_all_services_states(ambari_url, user, password, cluster_name):
    result = get(ambari_url, user, password,
                 '/api/v1/clusters/{0}/services?fields=ServiceInfo/state,ServiceInfo/maintenance_state'.format(cluster_name))
    service_state = json.loads(result.content)
    return service_state['items']


def get(ambari_url, user, password, path, connection_timeout=10):
    headers = {'X-Requested-By': 'ambari'}
    r = requests.get(ambari_url + path, auth=(user, password),
                     headers=headers, timeout=connection_timeout)
    return r


def put(ambari_url, user, password, path, data, connection_timeout=10):
    headers = {'X-Requested-By': 'ambari'}
    r = requests.put(ambari_url + path, data=data,
                     auth=(user, password), headers=headers, timeout=connection_timeout)
    return r


if __name__ == '__main__':
    main()
