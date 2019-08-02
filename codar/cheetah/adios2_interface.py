"""
ADIOS2 Interface
"""

import xml.etree.ElementTree as ET

"""
@TODO:
set_engine/transport/operation_parameter functions
"""

# A list of valid engines in adios2 and their parameters
_engines = {
    "BPFile": [
        "Threads",
        "Profile",
        "CollectiveMetadata",
        "ProfileUnits",
        "InitialBufferSize",
        "MaxBufferSize",
        "BufferGrowthFactor",
        "FlushStepsCount",
        "SubStreams",
        "node-local",
    ],
    "SST": [
        "RendezvousReaderCount",
        "RegistrationMethod",
        "QueueLimit",
        "QueueFullPolicy",
        "ReserveQueueLimit",
        "DataTransport",
        "ControlTransport",
        "NetworkInterface",
        "ControlInterface",
        "DataInterface",
        "FirstTimestepPrecious",
        "AlwaysProvideLatestTimestep",
        "OpenTimeoutSecs",
    ],
    "InSituMPI": [],
    "HDF5": [],
    "DataMan": [],
    "Inline": [
        "writerID",
    ],
    "BP4": ['node-local'],
}

# A list of valid transports and their parameters
_transports = {
    "File": [
        "Library",
    ],
    "WAN": [
        "Library",
    ],
}

# A list of valid variable operations and their parameters
_var_operations = {
    "zfp": [
        "rate",
        "Tolerance",
        "Precision",
    ],
    "sz": [],
    "blosc": [],
    "mgard": [],
    "png": [],
    "bzip2": [],
}


def get_adios_version(xml_file):
    """
    Get the ADIOS version of this xml file.

    :param xml_file: Path to the adios xml file
    :return: 1 (adios version 1) or 2 (adios version 2)
    """

    # Get the root and then the first child node
    # The 'tag' of that node should be 'io' for adios2, and
    # 'adios-group' for adios1
    tree = ET.parse(xml_file)
    root = tree.getroot()
    first_child_node = root.getchildren()[0]
    if first_child_node.tag == 'io':
        return 2
    return 1


def set_engine(xmlfile, io_obj, engine_type, parameters=None):
    """
    Set the engine type for an input IO object.

    :param xmlfile: String. The ADIOS2 xml file to be modified
    :param io_obj: String. Name of the io object which contains the engine
    :param engine_type: String. The engine type to be set for the io object
    :param parameters: List. A list of dicts containing 'key and 'value' keys
    :return: True on success, False on error
    """

    tree = ET.parse(xmlfile)
    io_node = _get_io_node(tree, io_obj)
    _validate_engine(engine_type, parameters)

    node = ET.Element("engine")
    node.set('type', engine_type)
    _add_parameters(node, parameters)

    _replace_and_add_elem(io_node, node, "engine")

    # Write the file back
    tree.write(xmlfile, xml_declaration=True)


def set_transport(xmlfile, io_obj, transport_type, parameters=None):
    """
    Set the transport type for an io object

    :param xmlfile: String. The ADIOS2 xml file to be modified
    :param io_obj: String. Name of the io object that contains the engine
    :param transport_type String. The transport type for this io object
    :param parameters: A dict containing the parameter keys and values
    :return: True on success, False on error
    """

    tree = ET.parse(xmlfile)
    io_node = _get_io_node(tree, io_obj)
    _validate_transport(transport_type, parameters)
    node = ET.Element("transport")
    node.set('type', transport_type)
    _add_parameters(node, parameters)

    _replace_and_add_elem(io_node, node, "transport")

    # Write the file back
    tree.write(xmlfile, xml_declaration=True)


def set_var_operation(xmlfile, io_obj, var_name, operation, parameters=None):
    """
    Set an operation on a variable

    :param xmlfile: String. The ADIOS2 xml file to be modified
    :param io_obj: String. Name of the io object that contains the engine
    :param var_name String. Name of the variable
    :param operation String. The operation to be performed on the variable
    :param parameters: A dict containing the parameter keys and values
    :return: True on success, False on error
    """

    tree = ET.parse(xmlfile)
    io_node = _get_io_node(tree, io_obj)
    _validate_var_operation(operation, parameters)

    oper_child = ET.Element("transport")
    oper_child.set('type', operation)
    _add_parameters(oper_child, parameters)

    # Check if a 'variable' element exists. If not, create one
    var_nodes = io_node.findall("variable")
    for varnode in var_nodes:
        if varnode.attrib['name'] == var_name:
            _replace_and_add_elem(varnode, oper_child, "operation")
            return

    # Not found. Create new
    new_var_node = ET.Element("variable")
    new_var_node.set("name", var_name)
    new_var_node.append(oper_child)
    io_node.append(new_var_node)

    # Write the file back
    tree.write(xmlfile, xml_declaration=True)


def _get_io_node(tree, io_obj):
    root = tree.getroot()
    for sub_element in root:
        if sub_element.attrib['name'] == io_obj:
            return sub_element

    raise Exception("Could not find io object matching {0}".format(io_obj))


def _add_parameters(node, parameters):
    if len(parameters) is 0:
        return

    for key, value in list(list(parameters)[0].items()):
        par_elem = ET.Element("parameter")
        par_elem.set('key', str(key))
        par_elem.set('value', str(value))
        node.append(par_elem)


def _replace_and_add_elem(parent, child, elem_tag):
    existing_node = parent.find(elem_tag)
    if existing_node is not None: parent.remove(existing_node)
    parent.append(child)


def _validate_engine(engine, parameters=None):
    engine_exists = engine in _engines
    if not engine_exists:
        raise Exception("{0} is not a valid ADIOS2 engine".format(engine))

    if not parameters: return
    _validate_parameters(parameters, _engines[engine], engine)


def _validate_transport(transport, parameters=None):
    transport_exists = transport in _transports
    if not transport_exists:
        raise Exception("{0} is not a valid ADIOS2 transport".format(
            transport))

    if not parameters: return
    _validate_parameters(parameters, _transports[transport], transport)


def _validate_var_operation(operation, parameters=None):
    var_oper_exists = operation in _var_operations
    if not var_oper_exists:
        raise Exception("{0} is not a valid ADIOS2 variable "
                        "operation".format(operation))

    if not parameters: return
    _validate_parameters(parameters, _var_operations[operation], operation)


def _validate_parameters(parameters, par_list, xml_elem):
    assert len(parameters) == 1
    param_dict = list(parameters)[0]
    for parameter in param_dict.keys():
        if parameter not in par_list:
            raise Exception("Parameter {0} is not a valid parameter for "
                            "{1}".format(parameter, xml_elem))


if __name__=="__main__":
    set_engine("test.xml", "writer", "SST", {"MarshalMethod":"FFS"})
    set_transport("test.xml", "writer", "WAN", {'Library':'MPI',
                                                'ProfileUnits':'Seconds'})
    set_var_operation("test.xml", "writer", "T", "zfp", {'rate':180})
