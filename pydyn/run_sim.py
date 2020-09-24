#!python3
#
# Copyright (C) 2014-2015 Julius Susanto. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

"""
PYPOWER-Dynamics
Time-domain simulation engine

"""

from pydyn.interface import init_interfaces
from pydyn.interface import init_interfaces0
from pydyn.mod_Ybus import mod_Ybus
from pydyn.version import pydyn_ver
from pydyn.bus_int import bus_int
from pydyn.sys_matrices_int import sys_matrices_int

from scipy.sparse.linalg import splu
import numpy as np

from pdb import set_trace as bp

from pypower.runpf import runpf
from pypower.ext2int import ext2int
from pypower.makeYbus import makeYbus
from pypower.idx_bus import BUS_I, BUS_TYPE, PD, QD, GS, BS, BUS_AREA, \
    VM, VA, VMAX, VMIN, LAM_P, LAM_Q, MU_VMAX, MU_VMIN, REF
from pypower.api import ppoption


def run_sim(ppc, elements, dynopt=None, events=None, recorder=None):
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

    # Get version information
    ver = pydyn_ver()
    print('PYPOWER-Dynamics ' + ver['Version'] + ', ' + ver['Date'])

    # Program options
    if dynopt:
        h = dynopt['h']
        t_sim = dynopt['t_sim']
        max_err = dynopt['max_err']
        max_iter = dynopt['max_iter']
        verbose = dynopt['verbose']
    else:
        # Default program options
        h = 0.01                # step length (s)
        t_sim = 5               # simulation time (s)
        # Maximum error in network iteration (voltage mismatches)
        max_err = 0.0001
        max_iter = 25           # Maximum number of network iterations
        verbose = False

    if dynopt['sample_period']:
        sample_rate = max(int(dynopt['sample_period']/h) - 1, 0)
    else:
        sample_rate = 0

    # Make lists of current injection sources (generators, external grids, etc) and controllers
    sources = []
    controllers = []
    for element in elements.values():
        if element.__module__ in ['pydyn.sym_order6a', 'pydyn.sym_order6b', 'pydyn.sym_order4', 'pydyn.ext_grid', 'pydyn.vsc_average', 'pydyn.asym_1cage', 'pydyn.asym_2cage']:
            sources.append(element)

        if element.__module__ == 'pydyn.controller':
            controllers.append(element)

    # Set up interfaces
    interfaces = init_interfaces(elements)
    interfaces0 = init_interfaces0(elements)

    # find events
    events_controllers = []

    # find blocks that create events in controllers
    for element_id in elements.keys():
        element = elements[element_id]
        if element.__module__ == 'pydyn.controller':
            for line in element.equations:
                if line[1] == 'EVENT':
                    new_event = [element_id, line[0], line[2]] + line[3:]
                    events_controllers.append(new_event)

    ##################
    # INITIALISATION #
    ##################
    print('Initialising models...')

    if not verbose:
        ppopt = ppoption(VERBOSE=0, OUT_ALL=0)
    else:
        ppopt = ppoption()
        #print('not verbose')

    # Run power flow and update bus voltages and angles in PYPOWER case object
    results, success = runpf(ppc, ppopt)
    ppc["bus"][:, VM] = results["bus"][:, VM]
    ppc["bus"][:, VA] = results["bus"][:, VA]

    # Build Ybus matrix
    ppc_int = ext2int(ppc)
    baseMVA, bus, branch = ppc_int["baseMVA"], ppc_int["bus"], ppc_int["branch"]
    Ybus, Yf, Yt = makeYbus(baseMVA, bus, branch)

    # Build modified Ybus matrix
    try:
        Ybus = mod_Ybus(Ybus, elements, bus, ppc_int['gen'], baseMVA)
    except:
        bp()
        Ybus = mod_Ybus(Ybus, elements, bus, ppc_int['gen'], baseMVA)

    # Calculate initial voltage phasors
    v0 = bus[:, VM] * (np.cos(np.radians(bus[:, VA])) +
                       1j * np.sin(np.radians(bus[:, VA])))

    # Initialise sources from load flow
    for source in sources:
        if source.__module__ in ['pydyn.asym_1cage', 'pydyn.asym_2cage']:
            # Asynchronous machine
            source_bus = ppc_int['bus'][source.bus_no, 0].astype(np.int64)
            v_source = v0[source_bus]
            source.initialise(v_source, 0)
        else:
            # Generator or VSC
            source_bus = ppc_int['gen'][source.gen_no, 0].astype(np.int64)
            S_source = np.complex(
                results["gen"][source.gen_no, 1] / baseMVA, results["gen"][source.gen_no, 2] / baseMVA)
            v_source = v0[source_bus]
            source.initialise(v_source, S_source)

    # initialise bus
    elements['bus'] = bus_int(ppc)
    elements['sys_matrices'] = sys_matrices_int(ppc)
    #elements['branch'] = ppc['branch']

    # Do we need interfaces0?
    # Interface controllers and machines (for initialisation)
    #for intf in interfaces:
    for k in range(len(interfaces)):
        intf = interfaces[k]
        intf0 = interfaces0[k]
        int_type = intf[0]
        var_name = intf0[1]
        source_var = intf[1]
        source_id = intf[2]
        dest_var = intf[3]
        dest_id = intf[4]
        if int_type == 'OUTPUT':
            # If an output, interface in the reverse direction for initialisation
            #intf[2].signals[var_name] = intf[3].signals[var_name]
            #if (intf0[2] != source_id) or (var_name != source_var) or (var_name != dest_var):
            #    bp()
            elements[source_id].signals[source_var] = elements[dest_id].signals[dest_var]
        else:
            # Inputs are interfaced in normal direction during initialisation
            #intf[3].signals[var_name] = intf[2].signals[var_name]
            #if (intf0[3] != dest_id)  or (var_name != source_var) or (var_name != dest_var):
            #    bp()
            elements[dest_id].signals[dest_var] = elements[source_id].signals[source_var]

        #try:
        #    element_source.signals[ var_name_source ] = element_dest.signals[ var_name_dest ]
        #except:
        #    bp()

    # Initialise controllers
    for controller in controllers:
        controller.initialise()

    #############
    # MAIN LOOP #
    #############

    sample_age = 0

    if events == None:
        print('Warning: no events!')

    # Factorise Ybus matrix
    Ybus_inv = splu(Ybus)

    y1 = []
    v_prev = v0
    print('Simulating...')
    for t in range(int(t_sim / h) + 1):
        if np.mod(t, 1/h) == 0 and verbose:
            print('t=' + str(t*h) + 's')

        # Interface controllers and machines
        #for intf in interfaces:
        for k in range(len(interfaces)):
            intf = interfaces[k]
            intf0 = interfaces0[k]

            var_name = intf0[1]
            source_var = intf[1]
            source_id = intf[2]
            dest_var = intf[3]
            dest_id = intf[4]
            #if var_name_dest not in element_dest.signals.keys():
            #bp()
            #element_dest.signals[ var_name_dest ] = element_source.signals[ var_name_source ]

            #if (intf0[2] != source_id) or (var_name != source_var) or (var_name != dest_var) or (intf0[3] != dest_id):
            #    bp()

            elements[dest_id].signals[dest_var] = elements[source_id].signals[source_var]
            #intf[3].signals[var_name] = intf[2].signals[var_name]

        # Solve differential equations
        for j in range(4):
            # Solve step of differential equations
            for element in elements.values():
                try:
                    element.solve_step(h, j)
                except:
                    bp()
                    element.solve_step(h, j)

            # Interface with network equations
            v_prev = solve_network(
                sources, v_prev, Ybus_inv, ppc_int, len(bus), max_err, max_iter)

        # check for events
        for event_c in events_controllers:
            new_event = None
            ctrl = event_c[0]
            ctrl_var = event_c[2]
            var_result = event_c[1]
            condition = elements[ctrl].signals[ctrl_var]
            if condition >= 1:
                #event_type = event_c[0]
                #node = event_c[1]
                new_event = [np.round(t*h, 5)] + event_c[3:]
                #print(new_event)
                try:
                    events.event_stack.append(new_event)
                    elements[ctrl].signals[var_result] = 1.0
                    #bp()
                except:
                    bp()
            else:
                elements[ctrl].signals[var_result] = 0.0

        if sample_age < sample_rate:
            sample_age += 1
        else:
            sample_age = 0
            if recorder != None:
                # Record signals or states
                recorder.record_variables(t*h, elements)

        if events != None:
            #if new_event != None:
            #    bp()
            # Check event stack
            ppc, refactorise = events.handle_events(
                np.round(t*h, 5), elements, ppc, baseMVA)

            if refactorise == True:
                # Rebuild Ybus from new ppc_int
                ppc_int = ext2int(ppc)
                baseMVA, bus, branch = ppc_int["baseMVA"], ppc_int["bus"], ppc_int["branch"]
                Ybus, Yf, Yt = makeYbus(baseMVA, bus, branch)

                # Rebuild modified Ybus
                Ybus = mod_Ybus(Ybus, elements, bus, ppc_int['gen'], baseMVA)

                # Refactorise Ybus
                Ybus_inv = splu(Ybus)

                # Solve network equations
                v_prev = solve_network(
                    sources, v_prev, Ybus_inv, ppc_int, len(bus), max_err, max_iter)

        # update the voltage in 'bus' matrix
        ppc['bus'][:, VM] = abs(v_prev)
        ppc['bus'][:, VA] = 2 * \
            np.arctan(v_prev.imag / (abs(v_prev) + v_prev.real))

        # update the system matrices
        elements['bus'].update(ppc)
        elements['sys_matrices'].update(ppc)

        #bp()

    return recorder


def solve_network(sources, v_prev, Ybus_inv, ppc_int, no_buses, max_err, max_iter):
    """
    Solve network equations
    """
    verr = 1
    i = 1
    # Iterate until network voltages in successive iterations are within tolerance
    while verr > max_err and i < max_iter:
        # Update current injections for sources
        I = np.zeros(no_buses, dtype='complex')
        for source in sources:
            if source.__module__ in ['pydyn.asym_1cage', 'pydyn.asym_2cage']:
                # Asynchronous machine
                source_bus = ppc_int['bus'][source.bus_no, 0].astype(np.int64)
            else:
                # Generators or VSC
                source_bus = ppc_int['gen'][source.gen_no, 0].astype(np.int64)

            I[source_bus] = source.calc_currents(v_prev[source_bus])

        # Solve for network voltages
        vtmp = Ybus_inv.solve(I)
        verr = np.abs(np.dot((vtmp-v_prev), np.transpose(vtmp-v_prev)))
        v_prev = vtmp
        i = i + 1

    if i >= max_iter:
        print('Network voltages and current injections did not converge in time step...')

    return v_prev
