#!python3


import numpy as np

class sys_matrices_int:
    def __init__(self, ppc):
        self.id = ''
        self.signals = {}
        self.initialise(ppc)


    def initialise(self, ppc):
        """
        create matrices
        """
        
        self.signals['bus'] = ppc['bus']
        self.signals['branch'] = ppc['branch']
        self.signals['gen'] = ppc['gen']

    def update(self, ppc):
        self.signals['bus'] = ppc['bus']
        self.signals['branch'] = ppc['branch']
        self.signals['gen'] = ppc['gen']
 

    def solve_step(self,h,dstep):
        """
        This element doesn't have dynamics
        """
        pass

