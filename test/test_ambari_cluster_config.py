import httpretty
from ambari_cluster_config import process_ambari_config
from mock import MagicMock
from ansible.module_utils.basic import AnsibleModule

# @httpretty.activate
# def test_one():
#     # define your patch:
#     httpretty.register_uri(httpretty.GET, "http://localhost:8080/api/v1/clusters",
#                         body="Find the best daily deals")

#     target = AnsibleModule(
#         argument_spec={}
#     )

    

#     process_ambari_config()