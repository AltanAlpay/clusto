from clusto.drivers.base import Device
from clusto.drivers.devices import PortMixin, IPMixin

class BasicServer(IPMixin, PortMixin, Device):
    """
    server
    """

    _clusto_type = "server"
    _driver_name = "basicserver"

    _properties = {'model':None,
                   'manufacturer':None}

    _portmeta = {'pwr-nema-5': {'numports':1},
                 'nic-eth': {'numports':2},
                 'console-serial' : { 'numports':1, }
                 }

    
class BasicVirtualServer(BasicServer):

    _driver_name = "basicvirtualserver"

    
    
        


