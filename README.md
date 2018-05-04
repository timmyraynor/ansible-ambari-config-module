# ansible-ambari-config-module
A module that update Ambari configuration through Ambari API

## Dependencies:

Python
- re
- requests
- time
- json


## How to include this module
1. Create a folder under your ansible playbook root path e.g. `extra_modules`
    
    mkdir <path-to-ansible-playbook>/extra_modules

2. Git clone this repository or copy the file across to the folder
   
    cp ambari_cluster_config.py <path-to-ansible-playbook>/extra_modules

3. Create an `ansible.cfg` file under your project root and add following line into it:

    library=./extra_modules

4. Start using this module




