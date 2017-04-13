import eventlet
from eventlet import tpool
eventlet.monkey_patch()  # noqa

from os_win import utilsfactory
from os_win.utils.compute import _clusapi_utils
from os_win.utils.compute import clusterutils
import wmi

import argparse
import json
import time
import logging

parser = argparse.ArgumentParser()
parser.add_argument('--log-file', required=False)

args = parser.parse_args()
LOG = logging.getLogger()

def setup_logging():
    log_level = logging.DEBUG

    handler = logging.StreamHandler()
    handler.setLevel(log_level)

    log_fmt = '[%(asctime)s] %(levelname)s - %(message)s'
    formatter = logging.Formatter(log_fmt)
    handler.setFormatter(formatter)

    LOG.addHandler(handler)
    LOG.setLevel(log_level)

    if args.log_file:
        handler = logging.FileHandler(args.log_file)
        handler.setLevel(log_level)
        handler.setFormatter(formatter)
        LOG.addHandler(handler)

setup_logging()


class BaseListener(object):
    def __init__(self):
        LOG.info("Starting [%s] event listener.",
                 self.__class__.__name__)

    def start(self):
        pass

    def stop(self):
        pass


class GroupStateChangeListener(BaseListener):
    _listener = None

    def __init__(self):
        super(GroupStateChangeListener, self).__init__()

        self._clusapi_utils = _clusapi_utils.ClusApiUtils()
        self._cluster_handle = self._clusapi_utils.open_cluster()

    def start(self):
        self._listener = clusterutils._ClusterGroupStateChangeListener(
            self._cluster_handle)
        eventlet.spawn_n(self._listen)

    def _listen(self):
        while True:
            event = self._listener.get()
            LOG.info("[GroupStateChangeListener] got event: %s",
                     json.dumps(event, indent=4))

    def stop(self):
        if self._listener:
            self._listener.stop()


class WMIObjDiffChecker(object):
    def get_props(self, wmi_obj):
        obj = wmi_obj.get_wrapped_object()
        props = {}

        # an MI object's length is the number of attributes the object it
        # represents has.
        for i in range(len(obj)):
            key, value_type, value = obj.get_element(i)
            props[key] = value

        return props

    def get_changed_attributes(self, wmi_obj_a, wmi_obj_b):
        obj_a_props = self.get_props(wmi_obj_a)
        obj_b_props = self.get_props(wmi_obj_b)

        obj_a_keys = set(obj_a_props.keys())
        obj_b_keys = set(obj_b_props.keys())

        if obj_a_keys != obj_b_keys:
            LOG.debug("Got different keys for the "
                      "compared objects. Using common ones.")
        common_keys = obj_a_keys & obj_b_keys

        changes = {key for key in common_keys
                   if obj_a_props[key] != obj_b_props[key]
                   and not isinstance(obj_a_props[key],
                                      wmi.mi.Instance)}
        return changes


class BaseWMIEventListener(BaseListener):
    _EVENT_TIMEOUT_MS = 2000
    _name_prop = "ElementName"

    def __init__(self, wmi_cls):
        super(BaseWMIEventListener, self).__init__()
        self._wmi_cls = wmi_cls
        self._class_name = wmi_cls.get_class_name()
        self._diff_checker = WMIObjDiffChecker()

    def _get_query(self, class_name, timeframe=1):
        query = ("SELECT * "
                 "FROM __InstanceModificationEvent "
                 "WITHIN %(timeframe)s "
                 "WHERE TargetInstance ISA '%(class)s' " %
                 {'class': class_name,
                  'timeframe': timeframe})
        return query

    def _callback(self, changed_wmi_obj):
        diff = self._diff_checker.get_changed_attributes(
            changed_wmi_obj, changed_wmi_obj.previous)
        msg = ("[%s] WMI change event: \n"
               "Element name: %s \n") % (self.__class__.__name__,
                                         getattr(changed_wmi_obj,
                                                 self._name_prop))
        for key in diff:
            msg += "%s: %s -> %s\n" % (key,
                                     getattr(changed_wmi_obj.previous, key),
                                     getattr(changed_wmi_obj, key))
        LOG.info(msg)

    def start(self):
        query = self._get_query(self._class_name)
        listener = self._wmi_cls.watch_for(raw_wql=query)

        def listener_loop():
            while True:
                try:
                    event = tpool.execute(listener,
                                          self._EVENT_TIMEOUT_MS)
                    self._callback(event)
                except wmi.x_wmi_timed_out:
                    pass
                except Exception:
                    LOG.exception('[%s] event listener loop '
                                  'encountered an '
                                  'unexpected exception.',
                                  self.__class__.__name__)
                    time.sleep(2)

        eventlet.spawn_n(listener_loop)


class VMChangeEventListener(BaseWMIEventListener):
    def __init__(self):
        conn = wmi.WMI(moniker='root/virtualization/v2')
        wmi_cls = conn.Msvm_ComputerSystem
        super(VMChangeEventListener, self).__init__(wmi_cls)


class ClusterResourceEventListener(BaseWMIEventListener):
    _name_prop = 'Name'

    def __init__(self):
        conn = wmi.WMI(moniker='root/MSCluster')
        wmi_cls = conn.MSCluster_Resource
        super(ClusterResourceEventListener, self).__init__(wmi_cls)


class ClusterGroupEventListener(BaseWMIEventListener):
    _name_prop = 'Name'

    def __init__(self):
        conn = wmi.WMI(moniker='root/MSCluster')
        wmi_cls = conn.MSCluster_ResourceGroup
        super(ClusterGroupEventListener, self).__init__(wmi_cls)

enabled_listeners = [VMChangeEventListener,
                     GroupStateChangeListener,
                     ClusterResourceEventListener,
                     ClusterGroupEventListener]

running_listeners = []
for listener_cls in enabled_listeners:
    listener = listener_cls()
    listener.start()
    running_listeners.append(listener)

try:
    while True:
        time.sleep(5)
except KeyboardInterrupt:
    LOG.info("Got KeyboardInterrupt event. Stopping listeners.")
    for listener in running_listeners:
        listener.stop()
