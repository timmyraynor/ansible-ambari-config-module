import httpretty
from ambari_cluster_config import process_ambari_config
from unittest.mock import MagicMock

@httpretty.activate
def test_one():
    # define your patch:
    # httpretty.register_uri(httpretty.GET, "http://localhost:8080/api/v1/clusters",
    #                     body="Find the best daily deals")

    # process_ambari_config()