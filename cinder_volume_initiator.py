# This is just a sample script. It could use some logging.

from os_brick.initiator import connector as brick_connector

from cinderclient.v2 import client as cinder_client
from cinderclient import service_catalog
 
DEFAULT_CINDER_CATALOG_INFO = 'volume:cinder:publicURL'
 
 
class CinderVolumeInitiator(object):
    """Used for requesting Cinder to expose/terminate connections."""
    def __init__(self, creds, auth_url):
        self.creds = creds
        self.auth_url = auth_url
 
    def _get_cinderclient(self, http_retries=10,
                          catalog_info=DEFAULT_CINDER_CATALOG_INFO,
                          allow_insecure=True):
        service_type, service_name, endpoint_type = catalog_info.split(':')
 
        c = cinder_client.Client(self.creds['username'],
                                 self.creds['password'],
                                 self.creds['tenant_name'],
                                 auth_url=self.auth_url,
                                 service_type=service_type,
                                 service_name=service_name,
                                 endpoint_type=endpoint_type,
                                 insecure=allow_insecure,
                                 retries=http_retries,
                                 cacert=self.creds.get('cacert'))
        # noauth extracts user_id:project_id from auth_token
        c.client.auth_token = self.creds.get('auth_token',
                                             '%s:%s' % (self.creds['username'],
                                                        self.creds['password']))
        c.client.management_url = self.auth_url
        return c
 
    def initialize_connection(self, volume_id, connector, mode='rw'):
        client = self._get_cinderclient()
 
        client.volumes.reserve(volume_id)
        try:
            connection_info = client.volumes.initialize_connection(volume_id, connector)
            client.volumes.attach(volume_id, instance_uuid=None, mountpoint=None,
                                  mode=mode, host_name=connector['host'])
            return connection_info
        except Exception:
            client.volumes.unreserve(volume_id)
            client.volumes.terminate_connection(volume_id, connector)
            raise
 
    def terminate_connection(self, volume_id, connector):
        client = self._get_cinderclient()
        client.volumes.terminate_connection(volume_id, connector)
        client.volumes.detach(volume_id)


class CinderVolumeConnector(object):
    # Uses the Cinder initiator to ensure volumes are presented to this host
    # and sets up the actual connections using os-brick. This is platform
    # independent.

    def __init__(self, initiator, initiator_ip, hostname,
                 root_helper=None, use_multipath=True,
                 device_scan_attempts=3):
        # The root helper would not be needed on Windows.
        self.initiator = initiator
        self.initiator_ip = initiator_ip
        self.hostname = hostname
        self.root_helper = root_helper
        self.use_multipath = use_multipath
        self.scan_attempts = device_scan_attempts

    def _get_brick_connector_info(self):
        conn = brick_connector.get_connector_properties(
            root_helper=None,
            my_ip=self.initiator_ip,
            multipath=self.use_multipath,
            # if multipath is requested, ensure it's honored.
            enforce_multipath=True,
            host=self.hostname)
        return conn

    def _get_brick_connector(self, connection_info):
        proto = connection_info.get('driver_volume_type')
        conn = connector.InitiatorConnector.factory(
            protocol=proto,
            root_helper=self.root_helper,
            use_multipath=self.use_multipath,
            device_scan_attempts=self.scan_attempts)

    def connect(self, volume_id, mode='rw'):
        connector_info = self._get_brick_connector_info()

        conn = None
        try:
            connection_info = self.initiator.initialize_connection(
                volume_id, connector_info, mode)
            conn = self._get_brick_connector(connection_info)
            # This dict will always contain a path, having the 'path' key.
            device_info = conn.connect_volume(connection_info['data'])

            # You may want to store this attachment info.
            attachment = dict(connection_info=connection_info,
                              device_info=device_info,
                              connector_info=connector_info)
            return attachment
        except Exception:
            if conn:
                conn.disconnect_volume(connection_info['data'])
            self.initiator.terminate_connection(volume_id,
                                                connector_info)

    def disconnect(self, volume_id, connection_info, connector_info=None):
        connector_info = connector_info or self._get_brick_connector_info()
        conn = self._get_brick_connector(connection_info)

        conn.disconnect_volume(connection_info)
        self.initiator.terminate_connection(volume_id, connector_info)


# Usage example:
#
# creds = dict(username='admin',
#              password='Passw0rd',
#              tenant_name='admin')
 
# auth_url = 'http://192.168.42.110:5000/v2.0'
 
# hostname =  'adcontroller'
# initiator_ip = '192.168.42.159'
# volume_id = '8ef424a4-2208-4e35-8d20-922938c6da2b'
 
# initiator = CinderVolumeInitiator(creds, auth_url)

# connector = CinderVolumeConnector(initiator, initiator_ip, hostname)
# attachment = connector.connect(volume_id)
# connector.disconnect(volume_id, attachment['connection_info'], attachment['connector_info'])
