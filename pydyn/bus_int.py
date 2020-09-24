#!python3


import numpy as np
from pypower.idx_bus import BUS_I, BUS_TYPE, PD, QD, GS, BS, BUS_AREA, \
    VM, VA, VMAX, VMIN, LAM_P, LAM_Q, MU_VMAX, MU_VMIN, REF

class bus_int:
    def __init__(self, ppc):
        self.id = ''
        self.signals = {}
        self.labels = []
        self.vars = {'Vm': VM, 'Va': VA, 'P': PD, 'Q': QD}
        self.update(ppc)


    def update(self, ppc):
        """
        create the bus element
        """
        
        n_buses = ppc['bus'].shape[0]
        for i in range(n_buses):
            #k = ppc['bus'][i, BUS_I]
            k = i
            for label in self.vars.keys():
                var_name = label + str(int( k ))
                self.signals[var_name] = ppc['bus'][i, self.vars[label] ]
        return

    '''
    def update(self, ppc):
        n_buses = ppc['bus'].shape[0]
        for i in range(n_buses):
            k = i
            for label in self.vars.keys():
                var_name = label + str(int( k ))
                self.signals[var_name] = ppc['bus'][i, self.vars[label] ]
        return
    '''

    def solve_step(self,h,dstep):
        """
        This element doesn't have dynamics
        """
        pass

