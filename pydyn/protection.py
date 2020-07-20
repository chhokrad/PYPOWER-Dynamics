from pypower.idx_bus import BUS_I, BUS_TYPE, PD, QD, GS, BS, BUS_AREA, \
    VM, VA, VMAX, VMIN, LAM_P, LAM_Q, MU_VMAX, MU_VMIN, REF, BASE_KV
from pypower.idx_brch import *
import numpy as np
from decimal import *

getcontext().prec = 6

class OverCurrentInstantaneousElement(object):
    def __init__(self, label, bus_to, bus_from, branch_data, branch_id, bus_data, I_max, interval):
        self.label = label
        self.interval = Decimal(str(interval))
        self.I_max = I_max
        self.bus_to_idx = bus_to
        self.bus_from_idx = bus_from
        self.bus_to_BaseKV = bus_data[bus_to, BASE_KV]
        self.bus_from_BaseKV = bus_data[bus_from, BASE_KV]
        self.R = branch_data[branch_id, BR_R] 
        self.X = branch_data[branch_id, BR_X]
        self.B = branch_data[branch_id, BR_B]
        self.ports = {"CMD_OPEN": False, "CMD_CLOSE": False}
        self.vars = {"I": None}
        self.current_state = "IDLE"
        self.connection = {}
        self.interval = Decimal(str(interval))

    def add_connection(self, internal_port, external_object):
        if internal_port in self.ports.keys():
            self.connection.update({internal_port: external_object})
            # self.connection[internal_port] = external_port_ref
    
    def step(self, vprev, events):
        print("State of the automaton {} before evalauting {}".format(
            self.label, self.current_state))
        if (self.current_state == "IDLE"):
            V1 = self.bus_to_BaseKV*np.abs(vprev[self.bus_to_idx])
            V2 = self.bus_from_BaseKV*np.abs(vprev[self.bus_from_idx])
            Y_series = np.abs(1/ (self.R + self.X))
            I =  (V1 - V2)* Y_series
            if (I > self.I_max):
                # print(I)
                self.current_state = "TRIPPED"
                self.ports["CMD_OPEN"] = True
                print("State of the automaton {} after evalauting {}".format(
                    self.label, self.current_state))
            return self.interval
        else :
            print("No change in the state of automaton {}".format(self.label))
            return self.interval
    
    def update_interfaces(self):
        for internal_port in self.connection:
            self.connection[internal_port].ports[internal_port] = self.ports[internal_port]

             

class Breaker(object):
    def __init__(self, label, tto, ttc, interval, branch_id):
        self.label = label
        self.branch_id  = branch_id
        self.time = Decimal(0)
        self.tto = Decimal(str(tto))
        self.ttc = Decimal(str(ttc))
        self.interval = Decimal(str(interval))
        self.current_state = "CLOSED"
        self.ports = {"CMD_OPEN":False, "CMD_CLOSE": False}
        self.vars = {'timer':Decimal(0)}
        self.connection = {}

    def add_connection(self, external_port, internal_port):
        if internal_port in self.ports.keys():
            self.connection[internal_port] = external_port
    
    def step(self, vprev, events):
        print("State of the automaton {} before evalauting {}".format(
            self.label, self.current_state))
        self.time = self.time + self.interval
        if (self.current_state ==  "CLOSED"):
            if (self.ports["CMD_OPEN"]):
                self.ports["CMD_OPEN"] = False
                self.current_state = "OPENING"
                self.vars["timer"] = self.interval 
                print("State of the automaton {} after evalauting {}".format(
                    self.label, self.current_state))
                return self.interval
        elif (self.current_state == "OPENING"):
            if (self.vars['timer'] >= self.tto):
                self.current_state = "OPEN"
                self.vars["timer"] = 0
                print("State of the automaton {} after evalauting {}".format(
                    self.label, self.current_state))
                # Add TRIP Event Here
                events.event_stack.append([ self.time, "TRIP_BRANCH", self.branch_id])
                return self.interval
            else :
                print("No change in the state of the automaton {}".format(self.label))
                self.vars['timer'] =  self.vars["timer"] + self.interval
        elif (self.current_state == "OPEN"):
            if (self.ports["CMD_CLOSE"]):
                self.current_state = "CLOSING"
                self.ports["CMD_CLOSE"] = False
                print("State of the automaton {} after evalauting {}".format(
                    self.label, self.current_state))
                return self.interval
        else :
            if (self.vars["timer"] >= self.ttc):
                self.current_state = "CLOSED"
                self.vars["timer"] = 0
                print("State of the automaton {} after evalauting {}".format(
                    self.label, self.current_state))
                # Add ATTACH Event Here
                return self.interval
            else:
                print("No change in the state of the automaton {}".format(self.label))
                self.vars["timer"] = self.vars["timer"] + self.interval
        return self.interval
    
    def update_interfaces(self):
        for internal_port in self.connection:
            self.connection[internal_port] = self.ports[internal_port]
