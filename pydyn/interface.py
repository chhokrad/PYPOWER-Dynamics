#!python3
#
# Copyright (C) 2014-2015 Julius Susanto. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

"""
PYPOWER-Dynamics
Functions for the interface between controller and machine variables

"""


def init_interfaces(elements):
    ints_list = []

    for element_id in elements.keys():
        element = elements[element_id]
        if element.__module__ == 'pydyn.controller':
            for line in element.equations:
                # define: type, source, destiny
                if line[1] == 'INPUT':
                    # new_int = [line[1],line[2],elements[line[3]],element]
                    source_var = line[2]
                    source_element = line[3]
                    dest_var = line[0]
                    dest_element = element_id
                    new_int = [line[1], source_var,
                               source_element, dest_var, dest_element]
                    ints_list.append(new_int)

                if line[1] == 'OUTPUT':
                    # new_int = [line[1],line[0],element,elements[line[3]]]
                    source_var = line[0]
                    source_element = element_id
                    dest_var = line[0]
                    dest_element = line[3]
                    new_int = [line[1], source_var,
                               source_element, dest_var, dest_element]
                    ints_list.append(new_int)

    return ints_list


def init_interfaces0(elements):
    ints_list = []

    for element_id in elements.keys():
        element = elements[element_id]
        if element.__module__ == 'pydyn.controller':
            for line in element.equations:
                # define: type, source, destiny
                if line[1] == 'INPUT':
                    new_int = [line[1], line[2], line[3], element_id]
                    ints_list.append(new_int)

                if line[1] == 'OUTPUT':
                    new_int = [line[1], line[0], element_id, line[3]]
                    ints_list.append(new_int)

    return ints_list
