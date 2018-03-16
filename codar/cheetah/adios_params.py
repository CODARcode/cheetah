"""
Functions for parsing and editing the ADIOS xml file to enable variable
transforms.  Transforms include compression and reduction. 'Transform'
is an ADIOS specific term.
"""

import xml.etree.cElementTree as ET


def adios_xml_transform(xml_filepath, group_name, var_name, value):
    """
    Edit the ADIOS XML file to enable transform (compression/reduction) for a
    variable

    :param group_name:   Name of the variable that will be transformed
    :param var_name:     Name of the variable that will be transformed
    :param value:        Transform type and options (sz, zfp etc.)
    :param xml_filepath: Aboslute path of the adios xml file. This will be in
                         the run directory.

    TODO: add error handling, tests, e.g. for when variable not found in XML
    file
    """

    tree = ET.parse(xml_filepath)

    tag = tree.find('adios-group[@name="%s"]/global-bounds/var[@name="%s"]'
                    % (group_name, var_name))
    tag.set('transform', value)
    tree.write(xml_filepath, xml_declaration=True)


def adios_xml_transport(xml_filepath, group_name, method_name, method_opts):
    tree = ET.parse(xml_filepath)

    elem = tree.find('method[@group="' + group_name + '"]')
    elem.set('method', method_name)
    elem.text = method_opts
    tree.write(xml_filepath, xml_declaration=True)


def xml_has_transport(xml_filepath, transport_type):
    """
    Check ADIOS XML file if provided transport method is present for any group
    :param xml_filepath: Path to the adios xml file
    :param transport_type: Transport type (POSIX, MPI, MPI_AGGREGATE,
    DATASPACES, DIMES, FLEXPATH)
    :return: True if transport type found, else false.
    """

    # Get tree in all lowercase to make search case-insensitive
    # _tree = ET.parse(xml_filepath)
    # tmp_tree = ET.tostring(_tree)
    # tmp_tree = tmp_tree.lower()
    # tree = ET.fromstring(tmp_tree)

    tree = ET.parse(xml_filepath)
    elem = tree.find('method[@method="' + transport_type + '"]')
    if elem is not None:
        return True
    return False

#if __name__ == "__main__":
 #   adios_xml_transform("heat:T", "sz", "/Users/kpu/vshare/scratch/heat_transfer.xml")
