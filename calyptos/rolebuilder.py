import yaml


class RoleBuilder():

    # Global list of roles
    ROLE_LIST = ['clc',
                 'user-facing',
                 'walrus',
                 'midonet-gw',
                 'cluster-controller',
                 'storage-controller',
                 'node-controller',
                 'midolman',
                 'mon-bootstrap',
                 'ceph-mons',
                 'ceph-osds',
                 'riak-head',
                 'riak-node',
                 'all']

    def __init__(self, environment_file='environment.yml'):
        self.environment_file = environment_file
        self.env_dict = self.get_all_attributes()
        self.roles = self.get_roles()
        self.all_hosts = self.roles['all']

    def read_environment(self):
        return yaml.load(open(self.environment_file).read())

    def get_all_attributes(self):
        env_dicts = self.read_environment()
        return env_dicts['default_attributes']

    def get_euca_attributes(self):
        try:
            return self.env_dict['eucalyptus']
        except:
            return None

    def get_riak_attributes(self):
        try:
            return self.env_dict['riakcs_cluster']
        except:
            return None

    def get_ceph_attributes(self):
        try:
            return self.env_dict['ceph']
        except:
            return None

    def _initialize_roles(self):
        roles = {}
        for role in self.ROLE_LIST:
            roles[role] = set()
        return roles

    def get_roles(self):
        roles = self._initialize_roles()
        euca_attributes = self.get_euca_attributes()
        ceph_attributes = self.get_ceph_attributes()
        riak_attributes = self.get_riak_attributes()

        roles['all'] = set([])

        if riak_attributes:
            riak_topology = riak_attributes['topology']
            if riak_topology['head']:
                roles['riak-head'] = set([riak_topology['head']['ipaddr']])
                roles['all'].add(riak_topology['head']['ipaddr'])
            else:
                raise Exception("No head node found for RiakCS cluster!")

            if riak_topology.get('nodes'):
                for n in riak_topology['nodes']:
                    roles['riak-node'].add(n)
                    roles['all'].add(n)

        if ceph_attributes:
            ceph_topology = ceph_attributes['topology']
            if ceph_topology['mon_bootstrap']:
                roles['mon-bootstrap'] = set([ceph_topology['mon_bootstrap']['ipaddr']])
                roles['all'].add(ceph_topology['mon_bootstrap']['ipaddr'])
            else:
                raise Exception("No Monitor found for bootstraping!")

            if ceph_topology.get('mons'):
                monset = set()
                for mon in ceph_topology['mons']:
                    monset.add(mon['ipaddr'])
                    roles['all'].add(mon['ipaddr'])
                roles['ceph-mons'] = monset

            if ceph_topology['osds']:
                osdset = set()
                for osd in ceph_topology['osds']:
                    osdset.add(osd['ipaddr'])
                    roles['all'].add(osd['ipaddr'])
                roles['ceph-osds'] = osdset
            else:
                raise Exception("No OSD Found!")

        if euca_attributes:
            topology = euca_attributes['topology']

            # Add CLC
            roles['clc'] = set([topology['clc-1']])
            roles['all'].add(topology['clc-1'])

            # Add UFS
            roles['user-facing'] = set(topology['user-facing'])
            for ufs in topology['user-facing']:
                roles['all'].add(ufs)

            # Add Walrus
            if 'walrus' in topology:
                roles['walrus'] = set([topology['walrus']])
                roles['all'].add(topology['walrus'])
            else:
                # No walrus defined assuming RiakCS
                roles['walrus'] = set()

            # Add cluster level components
            for name in topology['clusters']:
                roles['cluster'] = {}
                if 'cc-1' in topology['clusters'][name]:
                    cc = topology['clusters'][name]['cc-1']
                    roles['cluster-controller'].add(cc)
                else:
                    raise IndexError("Unable to find CC in topology for cluster " + name)

                if 'sc-1' in topology['clusters'][name]:
                    sc = topology['clusters'][name]['sc-1']
                    roles['storage-controller'].add(sc)
                else:
                    raise IndexError("Unable to find SC in topology for cluster " + name)

                roles['cluster'][name] = set([cc, sc])
                if 'nodes' in topology['clusters'][name]:
                    nodes = topology['clusters'][name]['nodes'].split()
                else:
                    raise IndexError("Unable to find nodes in topology for cluster " + name)
                for node in nodes:
                    roles['node-controller'].add(node)
                    roles['cluster'][name].add(node)
                roles['all'].update(roles['cluster'][name])

            # Add Midokura roles
            if euca_attributes['network']['mode'] == 'VPCMIDO':
                roles['midolman'] = roles['node-controller']
                roles['midonet-gw'] = roles['clc']
        return roles
