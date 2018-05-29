#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Documentation section
DOCUMENTATION = '''
---
module: ambari_component_extend
version_added: "1.0"
short_description: Add created hosts to existing service, e.g. add host to DATANODE component
  - Add created hosts to existing service, e.g. add host to DATANODE component
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
  service:
    description:
      The name of the service you want to start or stop(installed), use 'all' to stop all or start all
  component:
    description:
      The name of the component of the service to add host to
    required: yes
  add_host:
    description:
      The FQDN of the host to add to certain component
    required: yes
  retry:
    description:
      The time to retry to wait for request finished, default value is 60, depends on how many services you are trying to restart
  wait_interval:
    description:
      The wait interval between every retry, default value is 10s
'''

EXAMPLES = '''
# If you are aiming to provide a full file replacement / template replacement, please use the `lookup` plugin provided
# in native ansible

# NOT SUPPORT list:
  - Don't support any config that is not within Ambari config, so if the config file does not have a particular key
  you cannot add it.

# example:

  - name: Update a cluster configuration
    ambari_component_extend:
        protocol: http
        host: localhost
        port: 8080
        username: admin
        password: admin
        cluster_name: mycluster
        component: DATANODE
        add_host: amb1.service.consul

  - name: Update a cluster configuration
    ambari_component_extend:
        host: localhost
        port: 8080
        username: admin
        password: admin
        cluster_name: mycluster
        component: DATANODE
        add_host: amb1.service.consul
        retry: 10
        wait_interval: 10
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

import traceback


def main():

    argument_spec = dict(
        protocol=dict(type='str', default='http', required=False),
        host=dict(type='str', default=None, required=True),
        port=dict(type='int', default=None, required=True),
        username=dict(type='str', default=None, required=True),
        password=dict(type='str', default=None, required=True, no_log=True),
        cluster_name=dict(type='str', default=None, required=True),
        component=dict(type='str', default=None, required=True),
        add_host=dict(type='str', default=None, required=True),
        retry=dict(type='int', default=60, required=False),
        wait_interval = dict(type='int', default=10, required=False)
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
            msg='pyYaml library is required for this module')

    p = module.params

    protocol = p.get('protocol')
    host = p.get('host')
    port = p.get('port')
    username = p.get('username')
    password = p.get('password')
    cluster_name = p.get('cluster_name')
    component = p.get('component')
    hosttoadd = p.get('add_host')
    retry = p.get('retry')
    wait_interval = p.get('wait_interval')

    ambari_url = '{0}://{1}:{2}'.format(protocol, host, port)

    try:
        make_sure_host_exist(ambari_url, username,
                             password, cluster_name, hosttoadd)
        # Add components to the host
        check_response = get(ambari_url, username, password,
                             '/api/v1/clusters/{0}/hosts/{1}/host_components/{2}'.format(cluster_name, hosttoadd, component))
        if check_response.status_code == 200:
            module.exit_json(changed=False, result=check_response.content,
                             msg='Nothing changed, component [{0}] exist for host [{1}]'.format(component, hosttoadd))
        elif check_response.status_code == 404:
            add_response = post(ambari_url, username, password, '/api/v1/clusters/{0}/hosts/{1}/host_components/{2}'.format(
                cluster_name, hosttoadd, component), json.dumps({}))
            assert_status(add_response, ['200', '201', '202'])
            # Install components to hosts
            r = put(ambari_url, username, password, '/api/v1/clusters/{0}/hosts/{1}/host_components/{2}'.format(cluster_name, hosttoadd, component), json.dumps({
                'HostRoles': {
                    'state': 'INSTALLED'
                }
            }))
            assert_status(r, ['202'])
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
            while True and retry_counter < retry:
                progress, completed = wait_for_request_bounded(
                    cluster_name, ambari_url, username, password, request_meta)
                if completed:
                    module.exit_json(changed=True, results=progress)
                else:
                    time.sleep(wait_interval)
                    retry_counter = retry_counter + 1

            raise Exception('Max request waiting retries')
        else:
            raise Exception('Unknow status code from status check: {0}, response content: {1}'.format(
                check_response.status_code, check_response))

    except requests.ConnectionError as e:
        module.fail_json(
            msg="Could not connect to Ambari client: " + str(e.message), stacktrace=traceback.format_exc())
    except AssertionError as e:
        module.fail_json(msg=e.message, stacktrace=traceback.format_exc())
    except Exception as e:
        module.fail_json(
            msg="Ambari client exception occurred: " + str(e.message), stacktrace=traceback.format_exc())


def assert_status(response, expected):
    assert str(response.status_code) in expected, 'Expected response code unmatch: Exp[{0}], Actual[{1}] \n Message: {2}'.format(
        expected, response.status_code, response.content)


def make_sure_host_exist(ambari_url, username, password, cluster_name, hosttoadd):
    r = get(ambari_url, username, password,
            '/api/v1/clusters/{0}/hosts/{1}'.format(cluster_name, hosttoadd))
    if str(r.status_code) == '404':
        # Host not found, try to add host
        payload = {}
        create_host_response = put(ambari_url, username, password,
                                   '/api/v1/clusters/{0}/hosts/{1}'.format(cluster_name, hosttoadd), json.dumps(payload))
        assert_status(create_host_response, ['200', '201', '202'])
    elif str(r.status_code) == '200':
        pass
    else:
        raise AssertionError(
            'Status code for checking host registration not support: {0}'.format(str(r.status_code)))


def get(ambari_url, user, password, path, connection_timeout=10):
    headers = {'X-Requested-By': 'ambari'}
    r = requests.get(ambari_url + path, auth=(user, password),
                     headers=headers, timeout=connection_timeout)
    return r


def post(ambari_url, user, password, path, data, connection_timeout=10):
    headers = {'X-Requested-By': 'ambari'}
    r = requests.post(ambari_url + path, data=data,
                      auth=(user, password), headers=headers, timeout=connection_timeout)
    return r


def put(ambari_url, user, password, path, data, connection_timeout=10):
    headers = {'X-Requested-By': 'ambari'}
    r = requests.put(ambari_url + path, data=data,
                     auth=(user, password), headers=headers, timeout=connection_timeout)
    return r


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
        e.message = 'Request has failed due to: {0}'.format(res.content)
        raise
    if progress.get('Requests').get('request_status').upper() == 'COMPLETED':
        return progress, True
    else:
        return progress, False


if __name__ == '__main__':
    main()
