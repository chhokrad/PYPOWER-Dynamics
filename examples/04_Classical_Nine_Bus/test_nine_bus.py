#!python3
#
# Copyright (C) 2014-2015 Julius Susanto. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

"""
PYPOWER-Dynamics
Classical Stability Test

"""
# Dynamic model classes
from pydyn.ext_grid import ext_grid

# Simulation modules
from pydyn.events import events
from pydyn.recorder import recorder
from pydyn.run_sim import run_sim

# External modules
from pypower.loadcase import loadcase
import matplotlib.pyplot as plt
import numpy as np

# Protection Devices
from pydyn.executor import Executor
from pydyn.protection import Breaker, OverCurrentInstantaneousElement
    
if __name__ == '__main__':
    
    #########
    # SETUP #
    #########
    
    print('----------------------------------------')
    print('PYPOWER-Dynamics - Classical 9 Bus Test')
    print('----------------------------------------')

    # Load PYPOWER case
    ppc = loadcase('case9.py')

    # Relay Instantiation
    R1 = OverCurrentInstantaneousElement(
        "R1", 3, 9, ppc["branch"], 8, ppc["bus"], 100, 0.016)
    R2 = OverCurrentInstantaneousElement(
        "R2", 4, 9, ppc["branch"], 9, ppc["bus"], 100, 0.016)

    # Breaker Instantiation
    B1 = Breaker("B1", 0.040, 0.040, 0.002, 8)
    B2 = Breaker("B2", 0.040, 0.040, 0.002, 9)

    # Interface Initialization
    R1.add_connection("CMD_OPEN", B1)
    R1.add_connection("CMD_CLOSE", B1)
    R2.add_connection("CMD_OPEN", B2)
    R2.add_connection("CMD_CLOSE", B2)

    # Executor Instantiation
    E1 = Executor([R1, R2, B1, B2])
    
    # Program options
    dynopt = {}
    dynopt['h'] = 0.001               # step length (s)
    dynopt['t_sim'] = 1               # simulation time (s)
    dynopt['max_err'] = 1e-6          # Maximum error in network iteration (voltage mismatches)
    dynopt['max_iter'] = 25           # Maximum number of network iterations
    dynopt['verbose'] = True         # option for verbose messages
    dynopt['fn'] = 60                 # Nominal system frequency (Hz)
    
    # Integrator option
    dynopt['iopt'] = 'mod_euler'
    #dynopt['iopt'] = 'runge_kutta'
    
    # Create dynamic model objects
    G1 = ext_grid('GEN1', 0, 0.0608, 23.64, dynopt)
    G2 = ext_grid('GEN2', 1, 0.1198, 6.01, dynopt)
    G3 = ext_grid('GEN3', 2, 0.1813, 3.01, dynopt)
    
    # Create dictionary of elements
    elements = {}
    elements[G1.id] = G1
    elements[G2.id] = G2
    elements[G3.id] = G3
    
    # Create event stack
    oEvents = events('events.evnt')
    
    # Create recorder object
    oRecord = recorder('recorder.rcd')
    
    # Run simulation
    oRecord = run_sim(ppc,elements,dynopt,oEvents,oRecord, E1)
    
    # Calculate relative rotor angles
    rel_delta1 = np.array(oRecord.results['GEN2:delta']) - np.array(oRecord.results['GEN1:delta'])
    rel_delta2 = np.array(oRecord.results['GEN3:delta']) - np.array(oRecord.results['GEN1:delta']) 
    
    # Plot variables
    fig, ax = plt.subplots()
    ax.plot(oRecord.t_axis,rel_delta1 * 180 / np.pi, 'r-', oRecord.t_axis, rel_delta2 *180 / np.pi, 'b-')
    ax.plot(oRecord.t_axis, oRecord.results['GEN1:omega'])
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Rotor Angles (relative to GEN1)')
    plt.show()
    
    # Write recorded variables to output file
    #oRecord.write_output('output.csv')
