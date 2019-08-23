#!/usr/bin/python

import collections
import json

import openstack
from openstack import exceptions

# openstack.enable_logging(debug=False)

# Let's pick a microversion for which the host ids will show up properly.
DEFAULT_COMPUTE_MICROVERSION = '2.55'

def get_resource_providers(conn):
    response = conn.placement.get('/resource_providers')
    exceptions.raise_from_response(response)
    return [provider['uuid']
            for provider in response.json()['resource_providers']]


def get_provider_allocations(conn, provider_uuid):
    path = '/resource_providers/%s/allocations' % provider_uuid
    response = conn.placement.get(path)
    exceptions.raise_from_response(response)
    return response.json()['allocations']


def get_vm_allocations(conn):
    # We'll return a mapping between allocations and providers
    # so that we can easily spot stale/duplicate allocations.
    allocations = collections.defaultdict(dict)

    resource_providers = get_resource_providers(conn)
    for provider_id in resource_providers:
        provider_allocations = get_provider_allocations(conn, provider_id)
        for alloc_id, alloc_data in provider_allocations.items():
            if 'VCPU' not in alloc_data['resources']:
                # Doesn't look like a VM, we'll skip it.
                continue

            allocations[alloc_id][provider_id] = alloc_data

    return allocations


def get_existing_vms(conn, details=False, all_projects=True):
    return conn.compute.servers(details=details, all_projects=all_projects)


def get_duplicate_allocations(conn):
    duplicates = {}

    allocations = get_vm_allocations(conn)
    for alloc_id, alloc_data in allocations.items():
        if len(alloc_data) > 1:
            duplicates[alloc_id] = alloc_data
    return duplicates


def get_stale_allocations(conn):
    # Returns allocations for vms that no longer exist.
    # Note that it's expcted to have multiple allocations for
    # instances that are being migrated or resized but we're
    # not taking this into consideration (for now).
    vms = get_existing_vms(conn)
    allocations = get_vm_allocations(conn)

    vm_ids = [vm.id for vm in vms]
    stale_allocs = {
        alloc_id: alloc_data
        for alloc_id, alloc_data in allocations.items()
        if alloc_id not in vm_ids}

    return stale_allocs


def get_hypervisors(conn):
    return conn.compute.hypervisors()


def get_misplaced_allocations(conn):
    misplaced_allocations = collections.defaultdict(dict)

    allocations = get_vm_allocations(conn)
    hypervisors = get_hypervisors(conn)
    vms = get_existing_vms(conn, details=True)

    hypervisor_ids = {}
    vm_hosts = {}

    for hypervisor in hypervisors:
        hypervisor_ids[hypervisor.name] = hypervisor.id

    for vm in vms:
        vm_hosts[vm.id] = vm.hypervisor_hostname

    for alloc_id, alloc_data in allocations.items():
        # The vm doesn't exist anymore. There's a different
        # function that handles those.
        if alloc_id not in vm_hosts:
            continue

        for provider_id, resources in alloc_data.items():
            # We may have multiple allocations for the same instance.
            # Let's point out the ones that don't match
            if provider_id != hypervisor_ids[vm_hosts[alloc_id]]:
                misplaced_allocations[alloc_id][provider_id] = resources

    return misplaced_allocations

if __name__ == '__main__':
    # We expect credentials to be passed via env variables
    conn = openstack.connect()

    conn.compute.default_microversion = DEFAULT_COMPUTE_MICROVERSION

    all_vm_allocs = get_vm_allocations(conn)
    duplicate_allocs = get_duplicate_allocations(conn)
    stale_allocs = get_stale_allocations(conn)
    misplaced_allocations = get_misplaced_allocations(conn)

    print("NOTE: it's expected to have multiple allocations for "
          "instances that are being migrated or resized.")
    print("\n\nAllocations for missing/deleted instances: %s" %
          json.dumps(stale_allocs, indent=4))
    print("\n\nDuplicate allocations: %s" %
          json.dumps(duplicate_allocs, indent=4))
    print("\n\nMisplaced allocations: %s" %
          json.dumps(misplaced_allocations, indent=4))
    print("\n\nAll vm allocations: %s" %
          json.dumps(all_vm_allocs, indent=4))
