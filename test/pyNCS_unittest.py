#-----------------------------------------------------------------------------
# Purpose: Test pyNCS functions. Currently using pyAex module, but this should change in the future.
#
# Author: Emre Neftci
#
# Copyright : University of Zurich, Giacomo Indiveri, Emre Neftci, Sadique Sheik, Fabio Stefanini
# Licence : GPLv2
#-----------------------------------------------------------------------------

import pyNCS
import pyAex
import pyNCS.pyST as pyST
import time
import numpy as np
import unittest
import warnings
from pyAexServer import ServerStarter


def create_default_population(setup,chipname,N,*args,**kwargs):
    test_pops = pyNCS.Population('default', 'Default Population') 
    test_pops.populate_by_number(setup, 'seq', 'excitatory', N, *args, **kwargs)
    return test_pops


class TestSequenceFunctions(unittest.TestCase):

    def setUp(self):
        import expSetup
        self.nsetup = expSetup.nsetup

    def testBuildLinearPopulation(self):
        N=10
        #for transition populations + state populations (for inital and test)
        test_pops=create_default_population(self.nsetup,'seq',N)
        addrs=self.nsetup.mon[test_pops.soma.channel].addrLogicalConstruct([range(N)])
        for i,a in enumerate(test_pops.soma.laddr):
            self.assert_(a in addrs)

    def testMonitors(self):
        N=10
        test_pops=create_default_population(self.nsetup,'seq',N)
        stmon1=pyNCS.monitors.SpikeMonitor(test_pops.soma)
        stmon2=pyNCS.monitors.SpikeMonitor(test_pops.soma)
        self.nsetup.monitors.import_monitors([stmon1,stmon2])
        input_stim=test_pops.soma.spiketrains_poisson(100)
        self.nsetup.stimulate(input_stim)

        ird=input_stim[test_pops.soma.channel].raw_data()
        for mon in self.nsetup.monitors:
            ord=mon.sl.raw_data()
            for i in xrange(len(ird)):
                #self.assertAlmostEqual(ord[i][0],ird[i][0],2)
                self.assertAlmostEqual(ord[i][1],ird[i][1],2)

    def testPMapping(self):
        N=30
        p=0.25
        pyAex.MAPVERS=3
        s=create_default_population(self.nsetup, 'seq', N)
        t=create_default_population(self.nsetup, 'seq', N)
        m=pyNCS.PMapping('')
        m.__connect_random_all2all__(s.soma,t.synapses['excitatory0'],p=p)
        m.__connect_one2one__(s.soma,t.synapses['excitatory0'])
        P = int(p*127)
        for i in s.soma.paddr:
            for j in t.synapses['excitatory0'].paddr:
                self.assert_([i, j, P] in m.mapping)
        for n in range(len(s.soma.paddr)):
            self.assert_([s.soma.paddr[n], t.synapses['excitatory0'].paddr[n], P] in m.mapping)

        self.nsetup.prepare()

    def testPConnection(self):
        N=30
        p=0.25
        pyAex.MAPVERS=3
        s=create_default_population(self.nsetup, 'seq', N)
        t=create_default_population(self.nsetup, 'seq', N)
        c=pyNCS.PConnection(s,t,'excitatory0','random_all2all',{'p':0.25})
        m=c.mapping
        P = int(p*127)
        for i in s.soma.paddr:
            for j in t.synapses['excitatory0'].paddr:
                self.assert_([i, j, P] in m.mapping)
        for n in range(len(s.soma.paddr)):
            self.assert_([s.soma.paddr[n], t.synapses['excitatory0'].paddr[n], P] in m.mapping)

        self.nsetup.prepare()

    def testPopulationFunctions(self):
        N=5
        test_pops1=create_default_population(self.nsetup,'seq',N)
        test_pops2=create_default_population(self.nsetup,'seq',N,offset=N)
        pop=pyNCS.Population('', '')
        pop.init(self.nsetup, 'seq', 'excitatory')
        pop.union(test_pops1)
        pop.union(test_pops2)
        testaddr = np.concatenate([test_pops1.soma.paddr,test_pops2.soma.paddr])
        for a in testaddr:
            self.assertTrue(a in pop.soma.paddr)

    def testComAPI_RecordableCommunicatorBase(self):
        import pyNCS.ComAPI, os
        rec_com = pyNCS.ComAPI.RecordableCommunicatorBase()
        rec_com.run_rec(np.ones([0,2]))
        self.assertTrue(len(rec_com._rec_fns)==2)
        self.assertTrue(os.path.exists(rec_com._rec_fns[0]))
        self.assertTrue(os.path.exists(rec_com._rec_fns[1]))
        fns = rec_com.get_exp_rec() 
        self.assertTrue(len(rec_com._rec_fns)==0)

    def testExperimentTools(self):
        import pyNCS.experimentTools as et
        test_pops=create_default_population(self.nsetup,'seq', 5)
        stmon1=pyNCS.monitors.SpikeMonitor(test_pops.soma)
        stmon2=pyNCS.monitors.SpikeMonitor(test_pops.soma)
        self.nsetup.monitors.import_monitors([stmon1,stmon2])
        input_stim=test_pops.soma.spiketrains_poisson(100)
        self.nsetup.run(input_stim)
        et.mksavedir(pre='/tmp/test_et/')
        et.save_rec_files(self.nsetup)


    def tearDown(self):
        del self.nsetup

        
if __name__ == '__main__':
    unittest.main()
    

    #to debug
    #suite.debug()
    #or
    #TestSequenceFunctions('testStimulation').debug()

