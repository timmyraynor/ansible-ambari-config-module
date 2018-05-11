import httpretty
from extra_modules.ambari_cluster_config import process_ambari_config as ambari_config
import mock
from nose.tools import assert_equals
import json

sample_desire_config='''
{
  "href" : "http://localhost:8080/api/v1/clusters/mycluster?fields=Clusters/desired_configs",
  "Clusters" : {
    "cluster_name" : "mycluster",
    "version" : "HDP-2.5",
    "desired_configs" : {
      "mock_config_type" : {
        "tag" : "version1",
        "version" : 1
      }
    }
  }
}
'''

sample_config_detail='''
{
  "href" : "http://localhost:8080/api/v1/clusters/mycluster/configurations?type=mock_config_type&tag=version1",
  "items" : [
    {
      "href" : "http://localhost:8080/api/v1/clusters/mycluster/configurations?type=mock_config_type&tag=version1",
      "tag" : "version1",
      "type" : "mock_config_type",
      "version" : 1,
      "Config" : {
        "cluster_name" : "mycluster",
        "stack_id" : "HDP-2.5"
      },
      "properties" : {
        "content" : "test content",
        "is_supported_kafka_ranger" : "true",
        "key1": "mockvalue1",
        "key2": "mockvalue2"
      }
    }
  ]
}
'''

dummy_update_success_response = '{"dummy_key" : "dummy_value"}'


@httpretty.activate
@mock.patch('extra_modules.ambari_cluster_config.AnsibleModule')
def test_no_change(mock_module):
    # define your patch:
    httpretty.register_uri(httpretty.GET, "http://localhost:8080/api/v1/clusters/mycluster?fields=Clusters/desired_configs",
                           body=sample_desire_config)
    httpretty.register_uri(httpretty.GET, "http://localhost:8080/api/v1/clusters/mycluster/configurations?type=mock_config_type&tag=version1",
                           body=sample_config_detail)
    config_map = {
        'key1': {
            'value': 'mockvalue1'
        },
        'key2': {
            'value': 'mockvalue2'
        }
    }
    ambari_config(mock_module, 'localhost', 8080, 'username', 'password', 'mycluster', 'mock_config_type', None, config_map, True, 60)
    assert_equals(mock_module.fail_json.call_count, 0)
    assert_equals(mock_module.exit_json.call_count, 1)
    mock_module.exit_json.assert_called_with(changed=False, msg='No changes in config')


@httpretty.activate
@mock.patch('extra_modules.ambari_cluster_config.AnsibleModule')
def test_changes(mock_module):
    # define your patch:
    httpretty.register_uri(httpretty.GET, "http://localhost:8080/api/v1/clusters/mycluster?fields=Clusters/desired_configs",
                           body=sample_desire_config)
    httpretty.register_uri(httpretty.GET, "http://localhost:8080/api/v1/clusters/mycluster/configurations?type=mock_config_type&tag=version1",
                           body=sample_config_detail)
    httpretty.register_uri(httpretty.PUT, "http://localhost:8080/api/v1/clusters/mycluster",
                           body=json.loads(json.dumps(dummy_update_success_response).replace('\n','')))
    config_map = {
        'key1': {
            'value': 'mockvalue1'
        },
        'key2': {
            'value': 'changevalue2'
        }
    }
    ambari_config(mock_module, 'localhost', 8080, 'username', 'password', 'mycluster', 'mock_config_type', None, config_map, True, 60)
    assert_equals(mock_module.fail_json.call_count, 0)
    assert_equals(mock_module.exit_json.call_count, 1)
    mock_module.exit_json.assert_called_with(changed=True, msg=mock.ANY, results=mock.ANY)