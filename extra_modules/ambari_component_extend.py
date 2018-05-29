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
        service: HDFS
        component: DATANODE
        add_host: amb1.service.consul

  - name: Update a cluster configuration
    ambari_component_extend:
        host: localhost
        port: 8080
        username: admin
        password: admin
        cluster_name: mycluster
        service: HDFS
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
        service=dict(type='str', default=None, required=True),
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
    service_name = p.get('service')
    component = p.get('component')
    hosttoadd = p.get('add_host')
    retry = p.get('retry')
    wait_interval = p.get('wait_interval')

    ambari_url = '{0}://{1}:{2}'.format(protocol, host, port)
    services_fact = get_all_services_states(
        ambari_url, username, password, cluster_name)

    module.exit_json(changed=True)


if __name__ == '__main__':
    main()
