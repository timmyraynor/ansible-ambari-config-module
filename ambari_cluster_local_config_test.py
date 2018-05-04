import unittest
from ambari_cluster_local_config import parse_update_cluster_response

class AmbariClusterLocalConfigModuleTest(unittest.TestCase):
    def test_parse_update_cluster_response(self):
        changed_response = '''
            USERID=admin
            PASSWORD=admin
            PORT=:8080
            ########## Performing 'set' ipc.client.connection.maxidletime:30000 on (Site:core-site, Tag:version1525398970365466233)
            ########## Config found. Skipping origin value
            ########## PUTting json into: doSet_version1525399177782148678.json
            {
            "resources" : [
                {
                "href" : "http://localhost:8080/api/v1/clusters/dipa/configurations/service_config_versions?service_name=HDFS&service_config_version=3",
                "configurations" : [
                    {
                    "clusterName" : "dipa",
                    "stackId" : {
                        "stackName" : "HDP",
                        "stackVersion" : "2.5",
                        "stackId" : "HDP-2.5"
                    },
                    "type" : "core-site",
                    "versionTag" : "version1525399177782148678",
                    "version" : 3,
                    "serviceConfigVersions" : null,
                    "configs" : {
                        "io.serializations" : "org.apache.hadoop.io.serializer.WritableSerialization",
                        "hadoop.proxyuser.root.groups" : "*",
                        "hadoop.security.key.provider.path" : "",
                        "io.file.buffer.size" : "131072",
                        "ipc.client.connection.maxidletime" : "30000",
                        "hadoop.proxyuser.root.hosts" : "amb-server.service.consul",
                        "io.compression.codecs" : "org.apache.hadoop.io.compress.GzipCodec,org.apache.hadoop.io.compress.DefaultCodec,org.apache.hadoop.io.compress.SnappyCodec",
                        "hadoop.http.authentication.simple.anonymous.allowed" : "true",
                        "mapreduce.jobtracker.webinterface.trusted" : "false",
                        "hadoop.proxyuser.hdfs.groups" : "*",
                        "net.topology.script.file.name" : "/etc/hadoop/conf/topology_script.py",
                        "fs.trash.interval" : "360",
                        "ha.failover-controller.active-standby-elector.zk.op.retries" : "120",
                        "ipc.client.idlethreshold" : "8000",
                        "hadoop.proxyuser.hdfs.hosts" : "*",
                        "hadoop.security.authentication" : "simple",
                        "fs.defaultFS" : "hdfs://amb1.service.consul:8020",
                        "ipc.server.tcpnodelay" : "true",
                        "hadoop.security.auth_to_local" : "DEFAULT",
                        "hadoop.security.authorization" : "false",
                        "ipc.client.connect.max.retries" : "50"
            # export HADOOP_SLAVES=${HADOOP_HOME}/conf/slaves
                    },
                    "configAttributes" : {
                        "final" : {
                        "fs.defaultFS" : "true"
                        }
                    },
                    "propertiesTypes" : { }
                    }
                ],
                "group_id" : -1,
                "group_name" : "Default",
                "service_config_version" : 3,
                "service_config_version_note" : null,
                "service_name" : "HDFS"
                }
            ]
            }########## NEW Site:core-site, Tag:version1525399177782148678
        '''
        r, is_changed = parse_update_cluster_response(changed_response)
        self.assertTrue(is_changed)
        self.assertEqual(r, changed_response)


    def test_not_changed(self):
        not_changed_resp = '''
            USERID=admin
            PASSWORD=admin
            PORT=:8080
            ########## Performing 'set' ipc.client.connection.maxidletime:3000 on (Site:core-site, Tag:version1525398970365466233)
            ########## Config found. Skipping origin value
            ########## PUTting json into: doSet_version1525399175355132419.json
            ########## NEW Site:core-site, Tag:version1525398970365466233
        '''
        r, is_changed = parse_update_cluster_response(not_changed_resp)
        self.assertFalse(is_changed)
        self.assertEqual(r, not_changed_resp)


if __name__ == '__main__':
    unittest.main()