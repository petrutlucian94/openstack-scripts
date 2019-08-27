import collections
import json

import openstack
from openstack import exceptions
from os_win import utilsfactory
from oslo_utils import uuidutils

# Let's pick a microversion for which the host ids will show up properly.
DEFAULT_COMPUTE_MICROVERSION = '2.55'

# openstack.enable_logging(debug=False)

try:
    clusterutils = utilsfactory.get_clusterutils()
except Exception as ex:
    # This node may not be part of a cluster. Make sure you run this
    # within the targeted cluster.
    clusterutils = None


def pretty_dict(dict_obj):
    return json.dumps(dict_obj, indent=4)


def get_hypervisor_vms(host='.'):
    nova_vms = []
    other_vms = []

    try:
        vmutils = utilsfactory.get_vmutils(host=host)
        vm_mappings = vmutils.list_instance_notes()
    except Exception as ex:
        print("WARNING: Could not get hypervisor vms: %s" % host)
        return nova_vms, other_vms

    for vm_name, notes in vm_mappings:
        if notes and uuidutils.is_uuid_like(notes[0]):
            nova_vms.append(notes[0])
        else:
            other_vms.append(vm_name)

    return nova_vms, other_vms


def get_existing_vms(conn, details=True, all_projects=True):
    return list(
        conn.compute.servers(details=details, all_projects=all_projects))


def get_vm_cluster_groups():
    return clusterutils.list_instances() if clusterutils else []


def get_cluster_node_names():
    return clusterutils.get_cluster_node_names() if clusterutils else []


def get_nova_hypervisors(os_conn):
    return list(os_conn.compute.hypervisors())


def get_all_hypervisor_vms(hv_names):
    nova_vms = collections.defaultdict(dict)
    other_vms = {}
    for node_name in hv_names:
        _nova_vms, _other_vms = get_hypervisor_vms(node_name)
        other_vms[node_name] = _other_vms
        nova_vms[node_name] = _nova_vms
    return nova_vms, other_vms


def check_vm_states(hv_names):
    vm_state_map = collections.defaultdict(int)
    group_state_map = collections.defaultdict(int)

    for node_name in hv_names:
        try:
            vmutils = utilsfactory.get_vmutils(host=node_name)
            for vm_name in vmutils.list_instances():
                state = vmutils.get_vm_state(vm_name)
                vm_state_map[state] += 1

                if clusterutils and clusterutils.vm_exists(vm_name):
                    state_info = clusterutils.get_cluster_group_state_info(vm_name)
                    group_state_map[state_info['state']] += 1
        except Exception as ex:
            print("WARNING: Could not get hypervisor vms: %s" % node_name)

    # For now, we'll just print the amount of vms/groups
    # that are currently in a specific state.
    print("VM state map: %s" % pretty_dict(vm_state_map))
    print("Group state map: %s" % pretty_dict(group_state_map))


def check_clustered_nodes(nova_hv_names, cluster_node_names):
    unregistered_nodes = set(cluster_node_names) - set(nova_hv_names)
    unclustered_nodes = set(nova_hv_names) - set(cluster_node_names)

    print("Clustered nodes: %s" % cluster_node_names)
    print("Clustered nodes not registered in Nova: %s." % unregistered_nodes)
    if unregistered_nodes:
        print("WARNING: if Nova doesn't run on all the cluster nodes, "
              "instances that failover there will not be handled.")
    print("Unclustered nodes: %s" % unclustered_nodes)


def check_host_mappings(nova_vms, hv_vms):
    vm_to_host = {}
    for host, vms in hv_vms.items():
        for vm in vms:
            vm_to_host[vm] = host

    nova_db_mismatches = {}
    cluster_mismatches = {}
    unclustered_vms = []
    missing_vms = []

    nova_vm_ids = [vm.id for vm in nova_vms]
    hv_vm_ids = [vm for vm in vm_to_host]
    leaked_vms = set(hv_vm_ids) - set(nova_vm_ids)

    print("Leaked Nova vms: %s" % leaked_vms)

    for vm in nova_vms:
        if vm.id not in vm_to_host:
            missing_vms.append(vm.id)
            continue

        if vm.hypervisor_hostname != vm_to_host[vm.id]:
            nova_db_mismatches[vm.id] = dict(
                expected=vm.hypervisor_hostname,
                actual=vm_to_host[vm.id])

        if clusterutils:
            if not clusterutils.vm_exists(vm.instance_name):
                unclustered_vms.append(vm.id)
                continue

            cluster_node = clusterutils.get_vm_host(vm.instance_name)

            # This would be a race condition or failover cluster bug.
            if cluster_node != vm_to_host[vm.id]:
                cluster_mismatches[vm.id] = dict(
                    expected=cluster_node,
                    actual=vm_to_host[vm.id])
        else:
            unclustered_vms.append(vm.id)

    print("Missing vms: %s" % missing_vms)
    print("Nova db host mismatches: %s" % nova_db_mismatches)
    print("HV cluster host mismatches: %s" % cluster_mismatches)
    print("Unclustered VMs: %s" % unclustered_vms)

if __name__ == '__main__':
    # We expect credentials to be passed via env variables
    os_conn = openstack.connect()
    os_conn.compute.default_microversion = DEFAULT_COMPUTE_MICROVERSION

    nova_vms = get_existing_vms(os_conn, details=True)

    nova_hypervisors = get_nova_hypervisors(os_conn)
    cluster_node_names = get_cluster_node_names()

    nova_hv_names = [hypervisor.name for hypervisor in nova_hypervisors]

    check_clustered_nodes(nova_hv_names, cluster_node_names)

    nova_hv_vms, other_vms = get_all_hypervisor_vms(nova_hv_names)
    print("VMs created externally: %s" % other_vms)

    check_host_mappings(nova_vms, nova_hv_vms)

    check_vm_states(nova_hv_names)

    print("All hv vms: %s" % pretty_dict(nova_hv_vms))
