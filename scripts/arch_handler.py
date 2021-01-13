import random
import xmlstarlet
import sys

valid_switchblocks = ['wilton', 'universal', 'subset']
valid_topologies = ['on-cb-off-cb',
                    'on-cb-off-sb',
                    'on-cb-off-cbsb',
                    'on-cbsb-off-cbsb',
                    'on-sb-off-sb',
                    'single-wirelength',
                    'single-wirelength',
                    'single-wirelength',
                    'single-wirelength',
                    'single-wirelength']
valid_wirelengths = ['1', '2', '4', '8', '16',
                     '4-4', '4-8', '4-16', '2-4', '2-8', '2-16']

# key: length1, length2, 4LUT/6LUT, regular/prime
arch_map = {
    ('1', '', '6LUT', 'regular'): '6LUT/L1/k6_N10_topology-1.0sL1_22nm.xml',
    ('2', '', '6LUT', 'regular'): '6LUT/L2/k6_N10_topology-1.0sL2_22nm.xml',
    ('4', '', '6LUT', 'regular'): '6LUT/L4/k6_N10_topology-1.0sL4_22nm.xml',
    ('8', '', '6LUT', 'regular'): '6LUT/L8/k6_N10_topology-1.0sL8_22nm.xml',
    ('16', '', '6LUT', 'regular'): '6LUT/L16/k6_N10_topology-1.0sL16_22nm.xml',
    ('4', '4', '6LUT', 'regular'): '6LUT/L4-4/k6_N10_topology-0.85sL4-0.15gL4_22nm.xml',
    ('4', '8', '6LUT', 'regular'): '6LUT/L4-8/k6_N10_topology-0.85sL4-0.15gL8_22nm.xml',
    ('4', '16', '6LUT', 'regular'): '6LUT/L4-16/k6_N10_topology-0.85sL4-0.15gL16_22nm.xml',
    ('4', '4', '6LUT', 'prime'): '6LUT/L4-4/k6_N10_topology-0.55sL4-0.3spL4-0.15gL4_22nm.xml',
    ('4', '8', '6LUT', 'prime'): '6LUT/L4-8/k6_N10_topology-0.55sL4-0.3spL4-0.15gL8_22nm.xml',
    ('4', '16', '6LUT', 'prime'): '6LUT/L4-16/k6_N10_topology-0.55sL4-0.3spL4-0.15gL16_22nm.xml',

    ('1', '', '4LUT', 'regular'): '4LUT_DSP/L1/k4_N8_topology-1.0sL1_22nm.xml',
    ('2', '', '4LUT', 'regular'): '4LUT_DSP/L2/k4_N8_topology-1.0sL2_22nm.xml',
    ('4', '', '4LUT', 'regular'): '4LUT_DSP/L4/k4_N8_topology-1.0sL4_22nm.xml',
    ('8', '', '4LUT', 'regular'): '4LUT_DSP/L8/k4_N8_topology-1.0sL8_22nm.xml',
    # ('16', '',  '4LUT', 'regular'): '4LUT_DSP/L16/k4_N8_topology-1.0sL16_22nm.xml',
    ('2', '4', '4LUT', 'regular'): '4LUT_DSP/L2-4/k4_N8_topology-0.85sL2-0.15gL4_22nm.xml',
    ('2', '8', '4LUT', 'regular'): '4LUT_DSP/L2-8/k4_N8_topology-0.85sL2-0.15gL8_22nm.xml',
    ('2', '16', '4LUT', 'regular'): '4LUT_DSP/L2-16/k4_N8_topology-0.85sL2-0.15gL16_22nm.xml',
    ('2', '4', '4LUT', 'prime'): '4LUT_DSP/L2-4/k4_N8_topology-0.65sL2-0.2spL2-0.15gL4_22nm.xml',
    ('2', '8', '4LUT', 'prime'): '4LUT_DSP/L2-8/k4_N8_topology-0.65sL2-0.2spL2-0.15gL8_22nm.xml',
    ('2', '16', '4LUT', 'prime'): '4LUT_DSP/L2-16/k4_N8_topology-0.65sL2-0.2spL2-0.15gL16_22nm.xml'
}


# returns the full path to a reference architecture that has the specified parameters
def get_path_to_arch(arch_base, sb_pattern, wire_topology, wirelengths, global_via_repeat, fc_in, fc_out, lut_size):
    result = ''

    # Error Checks
    # wirelengths should match the topology
    if wire_topology != 'single-wirelength' and 'global' not in wirelengths:
        raise ArchException('Complex topologies must specify a global wirelength')

    if lut_size != '4LUT' and lut_size != '6LUT':
        raise ArchException('Illegal LUT size %d' % lut_size)

    # get path to reference architecture
    length1 = wirelengths['semi-global']
    length2 = ''

    if 'global' in wirelengths:
        length2 = wirelengths['global']

    arch_type = 'regular'
    if wire_topology == 'on-sb-off-sb' or wire_topology == 'on-cbsb-off-cbsb':
        arch_type = 'prime'

    arch_map_key = (str(length1), str(length2), lut_size, arch_type)

    if arch_map_key not in arch_map:
        raise ArchException('No arch map key: %s ' % (str(arch_map_key)))

    reference_arch_path = arch_base + '/' + arch_map[arch_map_key]

    replace_custom_switchblock(reference_arch_path, sb_pattern, wire_topology, wirelengths, global_via_repeat)
    replace_fc(reference_arch_path, wire_topology, wirelengths, fc_in, fc_out, True)
    replace_fc(reference_arch_path, wire_topology, wirelengths, 1.0, 1.0, False)
    if wire_topology != 'single-wirelength':
        replace_cb_depop(reference_arch_path, wirelengths['global'], global_via_repeat)

    result = reference_arch_path
    return result


def replace_cb_depop(arch_path, wirelength, via_repeat):
    result = ''
    for cb_index in range(0, wirelength, 1):
        char = '0'
        if cb_index % via_repeat == 0:
            char = '1'
        result += char + ' '

    to_node = '/architecture/segmentlist/segment[@name=\"l' + str(wirelength) + 'g\"]' + '/cb'
    result = '\"' + result + '\"'
    xml_update_expr(to_node, result, arch_path)


def replace_fc(arch_path, topology, wirelengths, fc_in: float, fc_out: float, is_clb: bool):
    to_node = '/architecture/tiles/tile/sub_tile'
    if is_clb is True:
        new_node = to_node + '[@name=' + '\"clb\"' + ']' + '/fc'

        xml_update_value(new_node, "in_val", str(fc_in), arch_path)
        xml_update_value(new_node, "out_val", str(fc_out), arch_path)
    else:
        for name in ['io', 'mult_36', 'memory']:
            new_node = to_node + '[@name=' + '\"' + name + '\"' + ']' + '/fc'
            xml_update_value(new_node, "in_val", str(fc_in), arch_path)
            xml_update_value(new_node, "out_val", str(fc_out), arch_path)

    # wire-type based overrides are specified for the on-cb-off-sb topology
    if topology == 'on-cb-off-sb':
        global_length = wirelengths['global']
        new_node = to_node + '/fc/fc_override[@segment_name=' + '\"' + 'l' + str(global_length) + 'g' + '\"' + ']'
        xml_update_value(new_node, "fc_val", str(fc_out), arch_path)


def replace_custom_switchblock(arch_path, sb_pattern, wire_topology, wirelengths, global_via_repeat):
    # check pattern type
    if sb_pattern not in valid_switchblocks:
        msg = 'Unrecognized switch pattern: ' + str(sb_pattern)
        raise ArchException(msg)

    # check topology type
    if wire_topology not in valid_topologies:
        msg = 'Unrecognized topology: ' + str(wire_topology)
        raise ArchException(msg)

    swb_list_node = '/architecture/switchblocklist'
    xml_delete_node(swb_list_node, arch_path)

    xml_add_subnode('/architecture', 'switchblocklist', arch_path)

    # Add turn core SWB
    swb_name = sb_pattern + '_turn_core'
    insert_switchblock(arch_path, swb_list_node, swb_name, 'unidir', 'CORE')

    swb_node = swb_list_node + '/' + 'switchblock' + '[@name=' + '\"' + swb_name + '\"' + ']'
    insert_switchblock_funcs(arch_path, swb_node, sb_pattern, False)
    insert_switchblock_wireconns(arch_path, swb_node, 'CORE', wire_topology, wirelengths, global_via_repeat)

    # Add turn perimeter SWB
    swb_name = sb_pattern + '_turn_perimeter'
    insert_switchblock(arch_path, swb_list_node, swb_name, 'unidir', 'PERIMETER')

    swb_node = swb_list_node + '/' + 'switchblock' + '[@name=' + '\"' + swb_name + '\"' + ']'
    insert_switchblock_funcs(arch_path, swb_node, sb_pattern, False)
    insert_switchblock_wireconns(arch_path, swb_node, 'PERIMETER', wire_topology, wirelengths, global_via_repeat)

    # Add straight SWB
    swb_name = sb_pattern + '_straight'
    insert_switchblock(arch_path, swb_list_node, swb_name, 'unidir', 'EVERYWHERE')

    swb_node = swb_list_node + '/' + 'switchblock' + '[@name=' + '\"' + swb_name + '\"' + ']'
    insert_switchblock_funcs(arch_path, swb_node, sb_pattern, True)
    insert_switchblock_wireconns(arch_path, swb_node, 'EVERYWHERE', wire_topology, wirelengths, global_via_repeat)


def insert_switchblock(arch_path, swb_list_node, name, sb_type, location_type):
    new_node_name = 'switchblock_new'
    xml_add_subnode(swb_list_node, new_node_name, arch_path)

    sw_node = swb_list_node + '/' + new_node_name
    xml_add_attribute(sw_node, 'name', name, arch_path)
    xml_add_attribute(sw_node, 'type', 'unidir', arch_path)

    sw_loc_node = 'switchblock_location'
    xml_add_subnode(sw_node, sw_loc_node, arch_path)
    sw_loc_node = sw_node + '/' + sw_loc_node
    xml_add_attribute(sw_loc_node, 'type', location_type, arch_path)

    xml_rename_node(sw_node, 'switchblock', arch_path)


def insert_switchblock_funcs(arch_path, sw_node, sb_pattern, is_straight):
    xml_add_subnode(sw_node, 'switchfuncs', arch_path)

    to_node = sw_node + '/switchfuncs'
    if is_straight is False:
        if sb_pattern == 'wilton':
            insert_sb_switch_func(arch_path, to_node, 'lt', 'W-t')
            insert_sb_switch_func(arch_path, to_node, 'lb', 't-1')
            insert_sb_switch_func(arch_path, to_node, 'rt', 't-1')
            insert_sb_switch_func(arch_path, to_node, 'br', 'W-t-2')
            insert_sb_switch_func(arch_path, to_node, 'tl', 'W-t')
            insert_sb_switch_func(arch_path, to_node, 'bl', 't+1')
            insert_sb_switch_func(arch_path, to_node, 'tr', 't+1')
            insert_sb_switch_func(arch_path, to_node, 'rb', 'W-t-2')
        elif sb_pattern == 'universal':
            insert_sb_switch_func(arch_path, to_node, 'lt', 'W-t-1')
            insert_sb_switch_func(arch_path, to_node, 'lb', 't')
            insert_sb_switch_func(arch_path, to_node, 'rt', 't')
            insert_sb_switch_func(arch_path, to_node, 'br', 'W-t-1')
            insert_sb_switch_func(arch_path, to_node, 'tl', 'W-t-1')
            insert_sb_switch_func(arch_path, to_node, 'bl', 't')
            insert_sb_switch_func(arch_path, to_node, 'tr', 't')
            insert_sb_switch_func(arch_path, to_node, 'rb', 'W-t-1')
        elif sb_pattern == 'subset':
            insert_sb_switch_func(arch_path, to_node, 'lt', 't')
            insert_sb_switch_func(arch_path, to_node, 'lb', 't')
            insert_sb_switch_func(arch_path, to_node, 'rt', 't')
            insert_sb_switch_func(arch_path, to_node, 'br', 't')
            insert_sb_switch_func(arch_path, to_node, 'tl', 't')
            insert_sb_switch_func(arch_path, to_node, 'bl', 't')
            insert_sb_switch_func(arch_path, to_node, 'tr', 't')
            insert_sb_switch_func(arch_path, to_node, 'rb', 't')
        else:
            raise ArchException('Unrecognized switch pattern: ' + str(sb_pattern))
    else:
        insert_sb_switch_func(arch_path, to_node, 'lr', 't')
        insert_sb_switch_func(arch_path, to_node, 'bt', 't')
        insert_sb_switch_func(arch_path, to_node, 'rl', 't')
        insert_sb_switch_func(arch_path, to_node, 'tb', 't')


def insert_switchblock_wireconns(arch_path, sw_node, type, topology, wirelengths, global_via_repeat):
    # get wirelengths
    length1 = wirelengths['semi-global']
    length2 = -1
    if 'global' in wirelengths:
        length2 = wirelengths['global']

    # check that global wirelength is defined if using a complex topology
    if length2 == -1 and topology != 'single-wirelength':
        raise ArchException('Topology ' + str(topology) + ' must specify a global wirelength!')

    len1_str = 'l' + str(length1)
    len2_str = 'l' + str(length2)

    # xml_add_subnode(sw_node, 'switchfuncs', arch_path)
    if topology == 'on-cb-off-cb':
        if type == 'CORE':
            for sp in range(0, length1, 1):
                insert_sb_wireconn(arch_path, sw_node, len1_str + 's', len1_str + 's', str(sp), '0')
            for sp in range(0, length2, global_via_repeat):
                insert_sb_wireconn(arch_path, sw_node, len2_str + 'g', len2_str + 'g', str(sp), '0')
        elif type == 'PERIMETER':
            fp = ''
            for sp in range(0, length1, 1):
                fp += '%d,' % sp
            fp = fp[:-1]
            insert_sb_wireconn(arch_path, sw_node, len1_str + 's', len1_str + 's', fp, '0')

            fp = ''
            for sp in range(0, length2, global_via_repeat):
                fp += '%d,' % sp
            fp = fp[:-1]
            insert_sb_wireconn(arch_path, sw_node, len2_str + 'g', len2_str + 'g', fp, '0')
        elif type == 'EVERYWHERE':
            insert_sb_wireconn(arch_path, sw_node, len1_str + 's', len1_str + 's', '0', '0')
            for sp in range(0, length2, global_via_repeat):
                insert_sb_wireconn(arch_path, sw_node, len2_str + 'g', len2_str + 'g', str(sp), '0')
        else:
            raise ArchException('Unknown SWB type: ' + type)
    elif topology == 'on-cb-off-sb' or topology == 'on-cb-off-cbsb':
        if type == 'CORE':
            for sp in range(0, length1, 1):
                insert_sb_wireconn(arch_path, sw_node, len1_str + 's', len1_str + 's', str(sp), '0')
            for sp in range(0, length2, global_via_repeat):
                insert_sb_wireconn(arch_path, sw_node, len2_str + 'g', len2_str + 'g', str(sp), '0')
            for sp in range(0, length2, global_via_repeat):
                insert_sb_wireconn(arch_path, sw_node, len2_str + 'g', len1_str + 's', str(sp), '0')
        elif type == 'PERIMETER':
            fp = ''
            for sp in range(0, length1, 1):
                fp += '%d,' % sp
            fp = fp[:-1]
            insert_sb_wireconn(arch_path, sw_node, len1_str + 's', len1_str + 's', fp, '0')

            fp = ''
            for sp in range(0, length2, global_via_repeat):
                fp += '%d,' % sp
            fp = fp[:-1]
            insert_sb_wireconn(arch_path, sw_node, len2_str + 'g', len2_str + 'g', fp, '0')

            fp = ''
            for sp in range(0, length2, global_via_repeat):
                fp += '%d,' % sp
            fp = fp[:-1]
            insert_sb_wireconn(arch_path, sw_node, len2_str + 'g', len1_str + 's', fp, '0')
        elif type == 'EVERYWHERE':
            insert_sb_wireconn(arch_path, sw_node, len1_str + 's', len1_str + 's', '0', '0')
            for sp in range(0, length2, global_via_repeat):
                insert_sb_wireconn(arch_path, sw_node, len2_str + 'g', len2_str + 'g', str(sp), '0')
            for sp in range(0, length2, global_via_repeat):
                insert_sb_wireconn(arch_path, sw_node, len2_str + 'g', len1_str + 's', str(sp), '0')
        else:
            raise ArchException('Unknown SWB type: ' + type)
    elif topology == 'on-cbsb-off-cbsb' or topology == 'on-sb-off-sb':
        if type == 'CORE':
            for sp in range(0, length1, 1):
                insert_sb_wireconn(arch_path, sw_node, len1_str + 's', len1_str + 's', str(sp), '0')
            for sp in range(0, length1, 1):
                insert_sb_wireconn(arch_path, sw_node, len1_str + 'sprime', len1_str + 'sprime', str(sp), '0')

            insert_sb_wireconn(arch_path, sw_node, len1_str + 'sprime', len2_str + 'g', '0', '0')
            for sp in range(0, length2, global_via_repeat):
                insert_sb_wireconn(arch_path, sw_node, len2_str + 'g', len2_str + 'g', str(sp), '0')
            for sp in range(0, length2, global_via_repeat):
                insert_sb_wireconn(arch_path, sw_node, len2_str + 'g', len1_str + 'sprime', str(sp), '0')
        elif type == 'PERIMETER':
            fp = ''
            for sp in range(0, length1, 1):
                fp += '%d,' % sp
            fp = fp[:-1]
            insert_sb_wireconn(arch_path, sw_node, len1_str + 's', len1_str + 's', fp, '0')
            insert_sb_wireconn(arch_path, sw_node, len1_str + 'sprime', len1_str + 'sprime', fp, '0')

            insert_sb_wireconn(arch_path, sw_node, len1_str + 'sprime', len2_str + 'g', '0', '0')
            fp = ''
            for sp in range(0, length2, global_via_repeat):
                fp += '%d,' % sp
            fp = fp[:-1]
            insert_sb_wireconn(arch_path, sw_node, len2_str + 'g', len2_str + 'g', fp, '0')
            insert_sb_wireconn(arch_path, sw_node, len2_str + 'g', len1_str + 'sprime', fp, '0')
        elif type == 'EVERYWHERE':
            insert_sb_wireconn(arch_path, sw_node, len1_str + 's', len1_str + 's', '0', '0')
            insert_sb_wireconn(arch_path, sw_node, len1_str + 'sprime', len1_str + 'sprime', '0', '0')
            insert_sb_wireconn(arch_path, sw_node, len1_str + 'sprime', len2_str + 'g', '0', '0')

            for sp in range(0, length2, global_via_repeat):
                insert_sb_wireconn(arch_path, sw_node, len2_str + 'g', len2_str + 'g', str(sp), '0')

            for sp in range(0, length2, global_via_repeat):
                insert_sb_wireconn(arch_path, sw_node, len2_str + 'g', len1_str + 'sprime', str(sp), '0')
        else:
            raise ArchException('Unknown SWB type: ' + type)
    elif topology == 'single-wirelength':
        if type == 'CORE':
            for sp in range(0, length1, 1):
                insert_sb_wireconn(arch_path, sw_node, len1_str + 's', len1_str + 's', str(sp), '0')
        elif type == 'PERIMETER':
            fp = ''
            for sp in range(0, length1, 1):
                fp += '%d,' % sp
            fp = fp[:-1]
            insert_sb_wireconn(arch_path, sw_node, len1_str + 's', len1_str + 's', fp, '0')
        elif type == 'EVERYWHERE':
            insert_sb_wireconn(arch_path, sw_node, len1_str + 's', len1_str + 's', '0', '0')
        else:
            raise ArchException('Unknown SWB type: ' + type)
    else:
        raise ArchException('Unrecognized topology: ' + str(topology))


def insert_sb_wireconn(arch_path: str, sw_node: str, from_type: str, to_type: str, from_sp: str, to_sp: str):
    new_wireconn = 'wireconn_new'
    xml_add_subnode(sw_node, new_wireconn, arch_path)
    new_wireconn_path = sw_node + '/' + new_wireconn
    xml_add_attribute(new_wireconn_path, 'from_type', from_type, arch_path)
    xml_add_attribute(new_wireconn_path, 'to_type', to_type, arch_path)
    xml_add_attribute(new_wireconn_path, 'from_switchpoint', from_sp, arch_path)
    xml_add_attribute(new_wireconn_path, 'to_switchpoint', to_sp, arch_path)

    xml_add_attribute(new_wireconn_path, 'num_conns', 'from', arch_path)
    xml_add_attribute(new_wireconn_path, 'from_order', 'fixed', arch_path)
    xml_add_attribute(new_wireconn_path, 'to_order', 'fixed', arch_path)

    xml_rename_node(new_wireconn_path, 'wireconn', arch_path)


def insert_sb_switch_func(arch_path, internal_path_to_node, sb_type, formula):
    xml_add_subnode(internal_path_to_node, 'func_new', arch_path)
    new_path = internal_path_to_node + '/func_new'
    xml_add_attribute(new_path, 'type', sb_type, arch_path)
    xml_add_attribute(new_path, 'formula', formula, arch_path)

    xml_rename_node(new_path, 'func', arch_path)


def xml_delete_node(internal_path_to_node: str, xml_file: str):
    ret = xmlstarlet.edit('-L', '-O', '-d', internal_path_to_node, xml_file)
    if ret != 0:
        print('ERROR: Trying to delete node: ' + internal_path_to_node + ' in ' + xml_file)
        sys.exit(1)


def xml_add_subnode(internal_path_to_node: str, name: str, xml_file: str):
    ret = xmlstarlet.edit('-L', '-O', '-s', internal_path_to_node, '-t', 'elem', '-n', name, xml_file)
    if ret != 0:
        print('ERROR: Trying to add subnode ' + name + ' at ' + internal_path_to_node + ' in ' + xml_file)
        sys.exit(1)


def xml_add_attribute(internal_path_to_node: str, attr_name: str, attr_value: str, xml_file: str):
    ret = xmlstarlet.edit('-L', '-O', '--insert', internal_path_to_node, '-t', 'attr', '-n', attr_name, '-v',
                          attr_value, xml_file)
    if ret != 0:
        print('ERROR: Trying to add attribute ' + attr_name + '(' + attr_value + ') at ' + internal_path_to_node
              + ' in ' + xml_file)
        sys.exit(1)


def xml_rename_node(internal_path_to_node: str, new_name: str, xml_file: str):
    ret = xmlstarlet.edit('-L', '-O', '-r', internal_path_to_node, '-v', new_name, xml_file)
    if ret != 0:
        print('ERROR: Trying to rename node ' + internal_path_to_node + ' to ' + new_name + ' in ' + xml_file)
        sys.exit(1)


def xml_update_value(internal_path_to_node: str, value_name: str, value: str, xml_file: str):
    internal_path_to_node = internal_path_to_node + '/@' + value_name
    ret = xmlstarlet.edit('-L', '-O', '-u', internal_path_to_node, '-v', value, xml_file)
    if ret != 0:
        print('ERROR: Trying to update value ' + internal_path_to_node + ' to ' + value + ' in ' + xml_file)
        sys.exit(1)


def xml_update_expr(internal_path_to_node: str, value: str, xml_file: str):
    ret = xmlstarlet.edit('-L', '-O', '-u', internal_path_to_node, '-x', value, xml_file)
    if ret != 0:
        print('ERROR: Trying to update expr ' + internal_path_to_node + ' to ' + value + ' in ' + xml_file)
        sys.exit(1)


# return the specified number of architectures that have the specified LUT size
def get_random_arch_names(num_archs, lut_size):
    if lut_size not in [4, 6]:
        raise ArchException('Invalid LUT size: %d' % lut_size)

    fc_in_vals = ['0.05', '0.1', '0.2', '0.4', '0.6']
    fc_out_vals = ['0.05', '0.1', '0.2', '0.4', '0.6']
    if lut_size == 4:
        fc_in_vals = ['0.1', '0.2', '0.3', '0.4', '0.6']
        fc_out_vals = ['0.1', '0.2', '0.3', '0.4', '0.6']

    arch_string_list = []

    while len(arch_string_list) != num_archs:

        # get random switch block pattern
        switchblock = random.choice(valid_switchblocks)

        # get random wirelength mix
        wirelength_mix = random.choice(valid_wirelengths)
        wirelengths = wirelength_mix.split('-')
        s_wirelength = wirelengths[0]
        g_wirelength = None
        if len(wirelengths) == 2:
            g_wirelength = wirelengths[1]

        # check that the wirelength mix makes sense with the given LUT size
        if ((lut_size == 4 and (
                wirelength_mix == '4-4' or wirelength_mix == '4-8' or wirelength_mix == '4-16' or wirelength_mix == '16'))
                or (lut_size == 6 and (
                        wirelength_mix == '2-4' or wirelength_mix == '2-8' or wirelength_mix == '2-16'))):
            continue

        # get random wire topology
        topology = random.choice(valid_topologies)

        # check that wire topology matches up with the wire mix
        if (g_wirelength is None and topology != 'single-wirelength') or (
                g_wirelength is not None and topology == 'single-wirelength'):
            continue

        # get random fc_in and fc_out
        fc_in = random.choice(fc_in_vals)
        fc_out = random.choice(fc_out_vals)

        # make the arch string
        arch_string = 'k%d_s%s_' % (lut_size, s_wirelength)
        if g_wirelength is not None:
            arch_string += 'g%s_' % g_wirelength
        arch_string += '%s_topology-%s_fcin%s_fcout%s' % (switchblock, topology, fc_in, fc_out)

        # check for duplicates
        if arch_string in arch_string_list:
            continue

        arch_string_list += [arch_string]

    return arch_string_list


class ArchException(BaseException):
    pass


if __name__ == '__main__':
    # Some test code
    wirelengths = {}
    lut_size = '4LUT'
    wirelengths['semi-global'] = 4
    # wirelengths['global'] = 4
    sb_pattern = 'universal'
    wire_topology = 'single-wirelength'
    global_via_repeat = 0
    fc_in = 0.77
    fc_out = 0.66

    arch_path = get_path_to_arch('/home/rustam/Projects/wotan/arch', sb_pattern, wire_topology, wirelengths, global_via_repeat, fc_in, fc_out, lut_size)

    print(arch_path)
    # arch_name_list = get_random_arch_names(100, 6)
    # for a in arch_name_list:
    #    print(a)
