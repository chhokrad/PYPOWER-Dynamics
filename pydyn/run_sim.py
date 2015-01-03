#!python3
#
# Copyright (C) 2014-2015 Julius Susanto
#
# PYPOWER-Dynamics is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published
# by the Free Software Foundation, either version 3 of the License,
# or (at your option) any later version.
#
# PYPOWER-Dynamics is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PYPOWER-Dynamics. If not, see <http://www.gnu.org/licenses/>.

"""
PYPOWER-Dynamics
Time-domain simulation engine

"""

from pydyn.interface import init_interfaces
from pydyn.mod_Ybus import mod_Ybus

from scipy.sparse.linalg import splu
import numpy as np

from pypower.runpf import runpf
from pypower.ext2int import ext2int
from pypower.makeYbus import makeYbus
from pypower.idx_bus import BUS_I, BUS_TYPE, PD, QD, GS, BS, BUS_AREA, \
    VM, VA, VMAX, VMIN, LAM_P, LAM_Q, MU_VMAX, MU_VMIN, REF
    
def run_sim(ppc, elements, events = None, recorder = None):
    """
    Run a time-domain simulation
    
    Inputs:
        ppc         PYPOWER load flow case
        elements    Dictionary of dynamic model objects (machines, controllers, etc) with Object ID as key
        events      Events object
        recorder    Recorder object (empty)
    
    Outputs:
        recorder    Recorder object (with data)
    """
    
    #########
    # SETUP #
    #########
    
    # Program options
    h = 0.01                # step length (s)
    t_sim = 15              # simulation time (s)
    max_err = 0.0001        # Maximum error in network iteration (voltage mismatches)
    max_iter = 25           # Maximum number of network iterations
    
    # Make lists of current injection sources (generators, external grids, etc) and controllers
    sources = []
    controllers = []
    for element in elements.values():
        if element.__module__ in ['pydyn.sym_order6', 'pydyn.sym_order4', 'pydyn.ext_grid']:
            sources.append(element)
            
        if element.__module__ == 'pydyn.controller':
            controllers.append(element)
    
    # Set up interfaces
    interfaces = init_interfaces(elements)
    
    ##################
    # INITIALISATION #
    ##################
    
    print('Initialising models...')
    
    # Run power flow and update bus voltages and angles in PYPOWER case object
    results, success = runpf(ppc) 
    ppc["bus"][:, VM] = results["bus"][:, VM]
    ppc["bus"][:, VA] = results["bus"][:, VA]
    
    # Build Ybus matrix
    ppc_int = ext2int(ppc)
    baseMVA, bus, branch = ppc_int["baseMVA"], ppc_int["bus"], ppc_int["branch"]
    Ybus, Yf, Yt = makeYbus(baseMVA, bus, branch)
    
    # Build modified Ybus matrix
    Ybus = mod_Ybus(Ybus, elements, bus, ppc_int['gen'], baseMVA)
    
    # Calculate initial voltage phasors
    v0 = bus[:, VM] * (np.cos(np.radians(bus[:, VA])) + 1j * np.sin(np.radians(bus[:, VA])))
    
    # Initialise sources from load flow
    for source in sources:
        source_bus = ppc_int['gen'][source.gen_no,0]
        S_source = np.complex(results["gen"][source.gen_no, 1] / baseMVA, results["gen"][source.gen_no, 2] / baseMVA)
        v_source = v0[source_bus]
        source.initialise(v_source,S_source)
    
    # Interface controllers and machines (for initialisation)
    for intf in interfaces:
        int_type = intf[0]
        var_name = intf[1]
        if int_type == 'OUTPUT':
            # If an output, interface in the reverse direction for initialisation
            intf[2].signals[var_name] = intf[3].signals[var_name]
        else:
            # Inputs are interfaced in normal direction during initialisation
            intf[3].signals[var_name] = intf[2].signals[var_name]
    
    # Initialise controllers
    for controller in controllers:
        controller.initialise()
    
    #############
    # MAIN LOOP #
    #############
    
    if events == None:
        print('Warning: no events!')
    
    # Factorise Ybus matrix
    Ybus_inv = splu(Ybus)
    
    y1 = []
    v_prev = v0
    print('Simulating...')
    for t in range(int(t_sim / h) + 1):
        if np.mod(t,1/h) == 0:
            print('t=' + str(t*h) + 's')
            
        # Interface controllers and machines
        for intf in interfaces:
            var_name = intf[1]
            intf[3].signals[var_name] = intf[2].signals[var_name]
        
        # Solve differential equations
        for element in elements.values():
            if element.__module__ in ['pydyn.sym_order6', 'pydyn.sym_order4', 'pydyn.controller', 'pydyn.ext_grid']:
                element.solve_step(h) 
        
        # Solve network equations
        verr = 1
        i = 1
        # Iterate until network voltages in successive iterations are within tolerance
        while verr > max_err and i < max_iter:        
            # Update current injections for sources
            I = np.zeros(len(bus), dtype='complex')
            for source in sources:
                source_bus = ppc_int['gen'][source.gen_no,0]
                I[source_bus] = source.calc_currents(v_prev[source_bus])
            
            # Solve for network voltages
            vtmp = Ybus_inv.solve(I) 
            verr = np.abs(np.dot((vtmp-v_prev),np.transpose(vtmp-v_prev)))
            v_prev = vtmp
            i = i + 1
            
        if recorder != None:
            # Record signals or states
            recorder.record_variables(t*h, elements)
        
        if events != None:
            # Check event stack
            ppc, refactorise = events.handle_events(t*h, elements, ppc, baseMVA)
            
            if refactorise == True:
                # Rebuild Ybus from new ppc_int
                ppc_int = ext2int(ppc)
                baseMVA, bus, branch = ppc_int["baseMVA"], ppc_int["bus"], ppc_int["branch"]
                Ybus, Yf, Yt = makeYbus(baseMVA, bus, branch)
                
                # Rebuild modified Ybus
                Ybus = mod_Ybus(Ybus, elements, bus, ppc_int['gen'], baseMVA)
                
                # Refactorise Ybus
                Ybus_inv = splu(Ybus)
                
                # TO DO: Solve network voltages and re-calculate current injections
                
    return recorder