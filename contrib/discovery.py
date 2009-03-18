from clusto.drivers import SimpleEntityNameManager, BasicServer, BasicVirtualServer, IPManager
from clusto.exceptions import ResourceException
import clusto
from IPy import IP

from traceback import format_exc
from subprocess import Popen, PIPE, STDOUT
from xml.etree import ElementTree
from os.path import exists
from pprint import pprint
import socket
import yaml
import sys
import re

SWITCHPORT_TO_RU = {
    1:1, 2:2, 3:3, 4:4, 5:5,
    6:7, 7:8, 8:9, 9:10, 10:11,
    11:13, 12:14, 13:15, 14:16, 15:17,
    16:19, 17:20, 18:21, 19:22, 20:23,

    21:1, 22:2, 23:3, 24:4, 25:5,
    26:7, 27:8, 28:9, 29:10, 30:11,
    31:13, 32:14, 33:15, 34:16, 35:17,
    36:19, 37:20, 38:21, 39:22, 40:23,
}

RU_TO_SWITCHPORT = {}
for port in SWITCHPORT_TO_RU:
    ru = SWITCHPORT_TO_RU[port]
    if not ru in RU_TO_SWITCHPORT or RU_TO_SWITCHPORT[ru] > port:
        RU_TO_SWITCHPORT[ru] = port

RU_TO_PWRPORT = {
    1: 'bb1',
    2: 'bb2',
    3: 'bb3',
    4: 'bb4',
    5: 'bb5',
    
    7: 'ba1',
    8: 'ba2',
    9: 'ba3',
    10: 'ba4',
    11: 'ba5',

    13: 'ab1',
    14: 'ab2',
    15: 'ab3',
    16: 'ab4',
    17: 'ab5',

    18: 'aa1',
    19: 'aa2',
    20: 'aa3',
    21: 'aa4',
    22: 'aa5',

    30: 'ab8',
    31: 'aa8',
    
    33: 'aa6',
    34: 'ba6',
    35: 'aa7',
    36: 'ba7',
}

hostpattern = re.compile('^\s*(?P<ip>[0-9A-z:.%]+)\s*(?P<hostname>[A-z\-0-9.]+)\s*$')
ETC_HOSTS = dict([(b['ip'], b['hostname']) for b in [a.groupdict() for a in [hostpattern.match(x) for x in file('/etc/hosts', 'r').readlines() if x] if a] if 'ip' in b and 'hostname' in b])

SSH_CMD = ['ssh', '-o', 'StrictHostKeyChecking no', '-o', 'PasswordAuthentication no']

def get_or_create(objtype, name):
    try:
        return clusto.getByName(name)
    except LookupError:
        return objtype(name)


def get_snmp_hostname(ipaddr, community='digg1t'):
    hostname = ''
    try:
        proc = Popen(['scli', '-c', 'show system info', '-x', ipaddr, community], stdout=PIPE)
        xmldata = proc.stdout.read()
        xmltree = ElementTree.fromstring(xmldata)
        hostname = list(xmltree.getiterator('name'))
    except:
        pass
    if len(hostname) > 0:
        hostname = hostname[0].text
    else:
        hostname = None
    return hostname

def get_ssh_hostname(ipaddr, username='root'):
    proc = Popen(SSH_CMD + ['%s@%s' % (username, ipaddr), 'hostname'], stdout=PIPE)
    output = proc.stdout.read()
    return output.rstrip('\r\n')

def get_hostname(ipaddr):
    hostname = None
    if ipaddr in ETC_HOSTS:
        hostname = ETC_HOSTS[ipaddr]

    if not hostname:
        hostname = get_snmp_hostname(ipaddr)

    if not hostname:
        try:
            hostname = socket.getfqdn(ipaddr)
        except: pass
    if not hostname:
        try:
            hostname = get_ssh_hostname(ipaddr)
        except: pass
    return hostname

def discover_interfaces(ipaddr, server=None, ssh_user='root'):
    #if not server:
    #   server = get_server(ipaddr)
    proc = Popen(SSH_CMD + ['%s@%s' % (ssh_user, ipaddr), '/sbin/ifconfig'], stdout=PIPE)
    output = proc.stdout.read()
    iface = {}
    for line in output.split('\n'):
        line = line.rstrip('\r\n')
        if not line: continue
        line = line.split('  ')
        if line[0]:
            name = line[0]
            iface[name] = []
            del line[0]
        line = [x for x in line if x]
        iface[name] += line

    for name in iface:
        attribs = {}
        value = None
        for attr in iface[name]:
            value = None
            if attr.startswith('Link encap') or \
                attr.startswith('inet addr') or \
                attr.startswith('Bcast') or \
                attr.startswith('Mask') or \
                attr.startswith('MTU') or \
                attr.startswith('Metric'):
                key, value = attr.split(':', 1)
            if attr.startswith('HWaddr'):
                key, value = attr.split(' ', 1)
            if attr.startswith('inet6 addr'):
                key, value = attr.split(': ', 1)
            if not value: continue
            attribs[key.lower()] = value
        iface[name] = attribs
    return iface

def get_facts(ipaddr, ssh_user='root'):
    proc = Popen(SSH_CMD + ['%s@%s' % (ssh_user, ipaddr), 'facter'], stdout=PIPE, stderr=STDOUT)
    facts = []
    for line in proc.stdout.read().split('\n'):
        line = line.rstrip('\r\n')
        if line:
            line = line.split(' => ', 1)
            if len(line) == 2:
                facts.append(line)
    return facts

def get_servertype(ipaddr, ssh_user='root'):
    proc = Popen(SSH_CMD + ['-l', ssh_user, ipaddr, 'cat /proc/xen/capabilities'], stdout=PIPE, stderr=STDOUT)
    stdout = proc.stdout.read().rstrip('\n')
    if stdout.find('No such file') != -1:
        # not a Xen kernel
        return BasicServer
    if stdout.find('control_d') != -1:
        # dom0
        return BasicServer
    # domU
    return BasicVirtualServer

def get_server(ipaddr):
    server = None
    fqdn = None

    try:
        return IPManager.getDevice(ipaddr)[0]
    except: pass

    try:
        names = clusto.getByName('servernames')
    except:
        names = SimpleEntityNameManager('servernames', basename='s', digits=4, startingnum=0)
    hostname = get_hostname(ipaddr)
    if hostname:
        if hostname.find('.') != -1:
            fqdn = hostname
            hostname = hostname.split('.', 1)[0]
        else:
            fqdn = hostname + '.digg.internal'

        server = clusto.getEntities(attrs=[{'key': 'fqdn', 'value': fqdn}])

        if server:
            server = server[0]
        else:
            print "Server %s doesn't exist in clusto... Creating it" % fqdn
            server = names.allocate(get_servertype(ipaddr))

    else:
        server = names.allocate(BasicServer)
        fqdn = server.name + '.digg.internal'
        return server

    if not fqdn in [x.value for x in server.attrs('fqdn')]:
        server.addFQDN(fqdn)

    fqdn = socket.gethostbyaddr(ipaddr)[0]
    if fqdn != ipaddr:
        if fqdn.find('.') == -1:
            fqdn += '.digg.internal'
        if fqdn and not fqdn in [x.value for x in server.attrs('fqdn')]:
            server.addFQDN(fqdn)

    clusto.commit()

    return server

def simple_ipbind(device, porttype='nic-eth', portnum=0):
    try:
        ip = IPManager.getIPs(device)
    except:
        ip = None

    if not ip:
        for fqdn in device.attrs('fqdn'):
            try:
                ip = socket.gethostbyname(fqdn)
                break
            except socket.gaierror:
                pass

    if not ip:
        try:
            ip = socket.gethostbyname(device.name)
        except socket.gaierror:
            pass

    if ip:
        try:
            ipman = IPManager.getIPs(device)
            if not ipman.getIPs(device):
                device.bindIPtoPort(ip, porttype, portnum)
                clusto.commit()
        except ResourceException:
            pass

    return ip
