#!/usr/bin/python

import collections
import json

import openstack
from openstack import exceptions

# openstack.enable_logging(debug=False)

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


def get_existing_vms(conn):
    return conn.compute.servers(details=False, all_projects=True)


def get_duplicate_allocations(conn):
    duplicates = {}

    allocations = get_vm_allocations(conn)
    for alloc_id, alloc_data in allocations.items():
        if len(alloc_data) > 1:
            duplicates[alloc_id] = alloc_data
    return duplicates


def get_stale_allocations(conn):
    # Returns allocations for vms that no longer exist.
    # Note that it's expected to have multiple allocations for
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


if __name__ == '__main__':
    # We expect credentials to be passed via env variables
    conn = openstack.connect()

    all_vm_allocs = get_vm_allocations(conn)
    duplicate_allocs = get_duplicate_allocations(conn)
    stale_allocs = get_stale_allocations(conn)

    print("NOTE: it's expected to have multiple allocations for "
          "instances that are being migrated or resized.")
    print("\n\nStale allocations: %s" %
          json.dumps(stale_allocs, indent=4))
    print("\n\nDuplicate allocations: %s" %
          json.dumps(duplicate_allocs, indent=4))
    print("\n\nAll vm allocations: %s" %
          json.dumps(all_vm_allocs, indent=4))
