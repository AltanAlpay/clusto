
import clusto
from clusto.test import testbase

from clusto.drivers import (VMManager, BasicServer, BasicVirtualServer,
                            ResourceTypeException)


class VMManagerTest(testbase.ClustoTestBase):

    def data(self):

        vmm = VMManager('vmm')

        s1 = BasicServer('s1')
        s1.add_attr('system', subkey='memory', value=16000)
        s1.add_attr('system', subkey='disk', value=5000)
        
        s2 = BasicServer('s2')
        s2.add_attr('system', subkey='memory', value=6000)
        s2.add_attr('system', subkey='disk', value=250)
        

        vmm.insert(s1)
        vmm.insert(s2)
        

    def testVMManagerAllocate(self):

        s1 = clusto.get_by_name('s1')
        s2 = clusto.get_by_name('s2')
        
        vs1 = BasicVirtualServer('vs1')
        vs1.add_attr('system', subkey='memory', value=1000)
        vs1.add_attr('system', subkey='disk', value=50)

        vs2 = BasicVirtualServer('vs2')
        vs2.add_attr('system', subkey='memory', value=8000)
        vs2.add_attr('system', subkey='disk', value=1000)

        vmm = clusto.get_by_name('vmm')

        vmm.allocate(vs1)

        self.assertEqual(len(vmm.resources(vs1)), 1)

        self.assert_(vmm.resources(vs1)[0].value in [s1, s2])

        vmm.allocate(vs2)

        self.assertEqual([r.value for r in vmm.resources(vs2)], [s2])



class EC2VMManagerTest(testbase.ClustoTestBase):

    def data(self):

        vmm = clusto.drivers.EC2VMManager('ec2man')

        
