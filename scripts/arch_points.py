import sys

from my_regex import *


# Contains info about an architecture data point. Basically mirrors
# the info contained in Wotan_Test_Suite, except for only one architecture point
class ArchPointInfo:

    def __init__(self, lut_size,  # size of the LUT (i.e. K)
                 s_wirelength,  # semi-global wirelength
                 g_wirelength,  # global-layer wirelength; specify None if not used
                 switchblock_pattern,  # wilton/universal/subset
                 wire_topology,
                 # 'single-wirelength', 'on-cb-off-cb', 'on-cb-off-sb', 'on-cb-off-cbsb', 'on-cbsb-off-cbsb', 'on-sb-off-sb'
                 fcin,  # cb input flexibility
                 fcout,  # cb output flexibility
                 arch_string=None):  # optional string that describes this architecture

        if lut_size not in [4, 6]:
            raise BaseException('Unexpected LUT size: %d' % (lut_size))

        if switchblock_pattern not in ['wilton', 'universal', 'subset']:
            raise BaseException('Unexpected switch block pattern: %s' % (switchblock_pattern))

        if wire_topology not in ['single-wirelength', 'on-cb-off-cb', 'on-cb-off-sb', 'on-cb-off-cbsb',
                                 'on-cbsb-off-cbsb', 'on-sb-off-sb']:
            raise BaseException('Unexpected wire topology: %s' % (wire_topology))

        self.lut_size = lut_size
        self.s_wirelength = s_wirelength
        self.g_wirelength = g_wirelength
        self.switchblock_pattern = switchblock_pattern
        self.wire_topology = wire_topology
        self.fcin = fcin
        self.fcout = fcout
        self.arch_string = arch_string

    # overload constructor -- initialize based on a string. Expecting string to be in the format of this class' 'as_str' function
    @classmethod
    def from_str(cls, s):
        # this should be a dictionary...
        regex_list = {
            's_wirelength': '.*_s(\d+)_.*',
            'g_wirelength': '.*_g(\d+)_.*',
            'K': '.*k(\d)_.*',
            'wire_topology': '.*_topology-([-\w]+)_.*',
            'fcin': '.*fcin(\d+\.*\d*)',
            'fcout': '.*fcout(\d+\.*\d*)',
        }

        # get wirelength, fcin, fcout
        tmp_dict = {}
        for key in regex_list:
            try:
                tmp_dict[key] = regex_last_token(s, regex_list[key])
            except RegexException as exception:
                if key == 'g_wirelength':
                    # it's OK if global wirelength wasn't specified
                    tmp_dict[key] = None
                    continue
                else:
                    raise

        s_wirelength = int(tmp_dict['s_wirelength'])
        g_wirelength = tmp_dict['g_wirelength']
        if g_wirelength != None:
            g_wirelength = int(g_wirelength)
        lut_size = int(tmp_dict['K'])
        wire_topology = tmp_dict['wire_topology']
        fcin = float(tmp_dict['fcin'])
        fcout = float(tmp_dict['fcout'])

        # get switchblock
        switchblock = None
        if 'subset' in s:
            switchblock = 'subset'
        elif 'universal' in s:
            switchblock = 'universal'
        elif 'wilton' in s:
            switchblock = 'wilton'
        else:
            print('could not find a switchblock specification in string:\n\t' + s)
            sys.exit()

        return cls(lut_size, s_wirelength, g_wirelength, switchblock, wire_topology, fcin, fcout, s)

    # returns a string describing an object of this class
    def as_str(self):
        return self.arch_string

    def __str__(self):
        return self.arch_string

    def __repr__(self):
        return self.arch_string


# returns a hard-coded list of Arch_Point_Info elements (use my_custom_arch_pair_list for pairwise comparisons)
def get_custom_arch_list():
    arch_list = []
    arch_strings = []

    # Legend (corresponds to arch_handler.py):
    # k<LUT_size>   s<semi-global segment length>    g<global segment length>    <switchblock (universal/subset/wilton)>
    #                  topology-<interconect topology>       fcin<input Fc>     fcout<output Fc>


    #arch_strings += ['k4_s2_g8_subset_topology-on-cb-off-cbsb_fcin0.3_fcout0.6']
    #arch_strings += ['k4_s2_g8_subset_topology-on-cb-off-cbsb_fcin0.6_fcout0.3']
    #arch_strings += ['k4_s2_g8_universal_topology-on-cb-off-cbsb_fcin0.3_fcout0.6']
    #arch_strings += ['k4_s2_g8_universal_topology-on-cb-off-cbsb_fcin0.6_fcout0.3']
    #arch_strings += ['k4_s2_g8_wilton_topology-on-cb-off-cbsb_fcin0.3_fcout0.6']
    #arch_strings += ['k4_s2_g8_wilton_topology-on-cb-off-cbsb_fcin0.6_fcout0.3']

    #arch_strings += ['k4_s2_g16_subset_topology-on-cb-off-cbsb_fcin0.3_fcout0.6']
    #arch_strings += ['k4_s2_g16_subset_topology-on-cb-off-cbsb_fcin0.6_fcout0.3']
    #arch_strings += ['k4_s2_g16_universal_topology-on-cb-off-cbsb_fcin0.3_fcout0.6']
    #arch_strings += ['k4_s2_g16_universal_topology-on-cb-off-cbsb_fcin0.6_fcout0.3']
    #arch_strings += ['k4_s2_g16_wilton_topology-on-cb-off-cbsb_fcin0.3_fcout0.6']
    #arch_strings += ['k4_s2_g16_wilton_topology-on-cb-off-cbsb_fcin0.6_fcout0.3']

    arch_strings += ['k4_s8_subset_topology-single-wirelength_fcin0.3_fcout0.6']
    arch_strings += ['k4_s8_subset_topology-single-wirelength_fcin0.6_fcout0.3']
    arch_strings += ['k4_s8_universal_topology-single-wirelength_fcin0.3_fcout0.6']
    arch_strings += ['k4_s8_universal_topology-single-wirelength_fcin0.6_fcout0.3']
    arch_strings += ['k4_s8_wilton_topology-single-wirelength_fcin0.3_fcout0.6']
    arch_strings += ['k4_s8_wilton_topology-single-wirelength_fcin0.6_fcout0.3']

    #### 100 random 4LUT architectures ####
    #arch_strings += ['k4_s1_subset_topology-single-wirelength_fcin0.7_fcout0.7']
    #arch_strings += ['k4_s1_subset_topology-single-wirelength_fcin0.7_fcout0.3']
    #arch_strings += ['k4_s1_subset_topology-single-wirelength_fcin0.3_fcout0.3']
    #arch_strings += ['k4_s1_subset_topology-single-wirelength_fcin0.3_fcout0.6']
    #arch_strings += ['k4_s1_subset_topology-single-wirelength_fcin0.3_fcout0.7']   
    #arch_strings += ['k4_s1_subset_topology-single-wirelength_fcin0.2_fcout0.4']
    #arch_strings += ['k4_s1_subset_topology-single-wirelength_fcin0.2_fcout0.2']
    #arch_strings += ['k4_s1_subset_topology-single-wirelength_fcin0.4_fcout0.2']

    # arch_strings += ['k4_s2_g16_wilton_topology-on-cbsb-off-cbsb_fcin0.2_fcout0.4']
    # arch_strings += ['k4_s1_wilton_topology-single-wirelength_fcin0.3_fcout0.2']
    # arch_strings += ['k4_s4_subset_topology-single-wirelength_fcin0.4_fcout0.2']
    # arch_strings += ['k4_s1_universal_topology-single-wirelength_fcin0.4_fcout0.2']
    # arch_strings += ['k4_s2_g8_wilton_topology-on-sb-off-sb_fcin0.1_fcout0.3']
    # arch_strings += ['k4_s2_wilton_topology-single-wirelength_fcin0.2_fcout0.1']
    # arch_strings += ['k4_s2_g16_subset_topology-on-cbsb-off-cbsb_fcin0.4_fcout0.4']
    # arch_strings += ['k4_s2_universal_topology-single-wirelength_fcin0.1_fcout0.1']
    # arch_strings += ['k4_s2_g16_subset_topology-on-sb-off-sb_fcin0.1_fcout0.1']
    # arch_strings += ['k4_s2_g16_subset_topology-on-cb-off-cbsb_fcin0.2_fcout0.2']
    # arch_strings += ['k4_s8_wilton_topology-single-wirelength_fcin0.1_fcout0.1']
    # arch_strings += ['k4_s2_g16_universal_topology-on-sb-off-sb_fcin0.1_fcout0.3']
    # arch_strings += ['k4_s2_g8_universal_topology-on-sb-off-sb_fcin0.3_fcout0.4']
    # arch_strings += ['k4_s8_wilton_topology-single-wirelength_fcin0.6_fcout0.1']
    # arch_strings += ['k4_s2_universal_topology-single-wirelength_fcin0.6_fcout0.4']
    # arch_strings += ['k4_s2_g16_subset_topology-on-cb-off-cbsb_fcin0.4_fcout0.3']
    # arch_strings += ['k4_s4_subset_topology-single-wirelength_fcin0.6_fcout0.6']
    # arch_strings += ['k4_s4_universal_topology-single-wirelength_fcin0.6_fcout0.1']
    # arch_strings += ['k4_s1_subset_topology-single-wirelength_fcin0.6_fcout0.6']
    # arch_strings += ['k4_s2_wilton_topology-single-wirelength_fcin0.6_fcout0.6']
    # arch_strings += ['k4_s4_wilton_topology-single-wirelength_fcin0.6_fcout0.4']
    # arch_strings += ['k4_s1_wilton_topology-single-wirelength_fcin0.6_fcout0.3']
    # arch_strings += ['k4_s2_g4_universal_topology-on-sb-off-sb_fcin0.6_fcout0.6']
    # arch_strings += ['k4_s1_universal_topology-single-wirelength_fcin0.6_fcout0.1']
    # arch_strings += ['k4_s2_g8_subset_topology-on-cb-off-cbsb_fcin0.1_fcout0.2']
    # arch_strings += ['k4_s2_g8_subset_topology-on-cb-off-sb_fcin0.3_fcout0.6']
    # arch_strings += ['k4_s2_g4_subset_topology-on-sb-off-sb_fcin0.3_fcout0.6']
    # arch_strings += ['k4_s8_universal_topology-single-wirelength_fcin0.3_fcout0.2']
    # arch_strings += ['k4_s1_subset_topology-single-wirelength_fcin0.2_fcout0.1']
    # arch_strings += ['k4_s2_g4_universal_topology-on-cbsb-off-cbsb_fcin0.1_fcout0.6']
    # arch_strings += ['k4_s1_subset_topology-single-wirelength_fcin0.6_fcout0.4']
    # arch_strings += ['k4_s1_subset_topology-single-wirelength_fcin0.2_fcout0.3']
    # arch_strings += ['k4_s2_g16_subset_topology-on-cb-off-sb_fcin0.3_fcout0.2']
    # arch_strings += ['k4_s2_g8_universal_topology-on-cbsb-off-cbsb_fcin0.4_fcout0.2']
    # arch_strings += ['k4_s4_wilton_topology-single-wirelength_fcin0.2_fcout0.1']
    # arch_strings += ['k4_s2_g4_wilton_topology-on-cb-off-sb_fcin0.3_fcout0.6']
    # arch_strings += ['k4_s4_wilton_topology-single-wirelength_fcin0.3_fcout0.6']
    # arch_strings += ['k4_s2_universal_topology-single-wirelength_fcin0.3_fcout0.2']
    # arch_strings += ['k4_s4_wilton_topology-single-wirelength_fcin0.6_fcout0.3']
    # arch_strings += ['k4_s2_subset_topology-single-wirelength_fcin0.1_fcout0.6']
    # arch_strings += ['k4_s2_g8_universal_topology-on-cb-off-cb_fcin0.3_fcout0.6']
    # arch_strings += ['k4_s4_subset_topology-single-wirelength_fcin0.6_fcout0.3']
    # arch_strings += ['k4_s1_wilton_topology-single-wirelength_fcin0.1_fcout0.4']
    # arch_strings += ['k4_s8_universal_topology-single-wirelength_fcin0.3_fcout0.4']
    # arch_strings += ['k4_s2_subset_topology-single-wirelength_fcin0.2_fcout0.3']
    # arch_strings += ['k4_s1_universal_topology-single-wirelength_fcin0.1_fcout0.6']
    # arch_strings += ['k4_s2_g4_wilton_topology-on-cb-off-sb_fcin0.6_fcout0.2']
    # arch_strings += ['k4_s2_g4_subset_topology-on-sb-off-sb_fcin0.6_fcout0.3']
    # arch_strings += ['k4_s4_wilton_topology-single-wirelength_fcin0.4_fcout0.6']
    # arch_strings += ['k4_s4_subset_topology-single-wirelength_fcin0.6_fcout0.4']
    # arch_strings += ['k4_s2_g16_universal_topology-on-cbsb-off-cbsb_fcin0.3_fcout0.3']
    # arch_strings += ['k4_s2_wilton_topology-single-wirelength_fcin0.3_fcout0.1']
    # arch_strings += ['k4_s8_subset_topology-single-wirelength_fcin0.3_fcout0.6']
    # arch_strings += ['k4_s2_g16_subset_topology-on-sb-off-sb_fcin0.4_fcout0.2']
    # arch_strings += ['k4_s2_g16_universal_topology-on-cb-off-cb_fcin0.1_fcout0.2']
    # arch_strings += ['k4_s4_wilton_topology-single-wirelength_fcin0.2_fcout0.3']
    # arch_strings += ['k4_s2_subset_topology-single-wirelength_fcin0.4_fcout0.2']
    # arch_strings += ['k4_s4_universal_topology-single-wirelength_fcin0.4_fcout0.6']
    # arch_strings += ['k4_s2_g8_subset_topology-on-cb-off-sb_fcin0.3_fcout0.1']
    # arch_strings += ['k4_s2_g4_wilton_topology-on-cb-off-sb_fcin0.1_fcout0.6']
    # arch_strings += ['k4_s2_g16_subset_topology-on-cb-off-cb_fcin0.3_fcout0.4']
    # arch_strings += ['k4_s2_g8_universal_topology-on-cb-off-cb_fcin0.4_fcout0.2']
    # arch_strings += ['k4_s8_wilton_topology-single-wirelength_fcin0.2_fcout0.3']
    # arch_strings += ['k4_s2_universal_topology-single-wirelength_fcin0.1_fcout0.3']
    # arch_strings += ['k4_s2_g16_universal_topology-on-cb-off-sb_fcin0.1_fcout0.3']
    # arch_strings += ['k4_s2_g4_wilton_topology-on-cb-off-cb_fcin0.4_fcout0.6']
    # arch_strings += ['k4_s4_wilton_topology-single-wirelength_fcin0.3_fcout0.3']
    # arch_strings += ['k4_s2_g4_universal_topology-on-cb-off-sb_fcin0.3_fcout0.3']
    # arch_strings += ['k4_s2_g8_universal_topology-on-cb-off-sb_fcin0.6_fcout0.6']
    # arch_strings += ['k4_s4_wilton_topology-single-wirelength_fcin0.1_fcout0.6']
    # arch_strings += ['k4_s2_g8_universal_topology-on-cbsb-off-cbsb_fcin0.4_fcout0.4']
    # arch_strings += ['k4_s8_subset_topology-single-wirelength_fcin0.1_fcout0.2']
    # arch_strings += ['k4_s8_subset_topology-single-wirelength_fcin0.6_fcout0.6']
    # arch_strings += ['k4_s2_g4_subset_topology-on-sb-off-sb_fcin0.2_fcout0.3']
    # arch_strings += ['k4_s2_g16_universal_topology-on-cb-off-sb_fcin0.3_fcout0.3']
    # arch_strings += ['k4_s1_universal_topology-single-wirelength_fcin0.6_fcout0.4']
    # arch_strings += ['k4_s2_g16_subset_topology-on-cbsb-off-cbsb_fcin0.6_fcout0.6']
    # arch_strings += ['k4_s2_g8_wilton_topology-on-cb-off-cb_fcin0.1_fcout0.1']
    # arch_strings += ['k4_s2_g8_subset_topology-on-cbsb-off-cbsb_fcin0.3_fcout0.3']
    # arch_strings += ['k4_s8_wilton_topology-single-wirelength_fcin0.1_fcout0.4']
    # arch_strings += ['k4_s2_g16_universal_topology-on-cb-off-cbsb_fcin0.2_fcout0.4']
    # arch_strings += ['k4_s2_g4_subset_topology-on-cb-off-sb_fcin0.1_fcout0.4']
    # arch_strings += ['k4_s2_g8_wilton_topology-on-cbsb-off-cbsb_fcin0.3_fcout0.1']
    # arch_strings += ['k4_s8_universal_topology-single-wirelength_fcin0.6_fcout0.3']
    # arch_strings += ['k4_s4_wilton_topology-single-wirelength_fcin0.4_fcout0.4']
    # arch_strings += ['k4_s2_g4_subset_topology-on-cb-off-cb_fcin0.3_fcout0.6']
    # arch_strings += ['k4_s2_g16_universal_topology-on-sb-off-sb_fcin0.1_fcout0.1']
    # arch_strings += ['k4_s2_g8_universal_topology-on-cbsb-off-cbsb_fcin0.3_fcout0.6']
    # arch_strings += ['k4_s4_subset_topology-single-wirelength_fcin0.4_fcout0.6']
    # arch_strings += ['k4_s2_g8_wilton_topology-on-cb-off-sb_fcin0.2_fcout0.1']
    # arch_strings += ['k4_s2_wilton_topology-single-wirelength_fcin0.2_fcout0.6']
    # arch_strings += ['k4_s1_subset_topology-single-wirelength_fcin0.6_fcout0.3']
    # arch_strings += ['k4_s2_wilton_topology-single-wirelength_fcin0.4_fcout0.4']
    # arch_strings += ['k4_s1_universal_topology-single-wirelength_fcin0.4_fcout0.1']
    # arch_strings += ['k4_s2_g16_wilton_topology-on-cb-off-sb_fcin0.1_fcout0.2']
    # arch_strings += ['k4_s8_universal_topology-single-wirelength_fcin0.2_fcout0.1']
    # arch_strings += ['k4_s2_g4_subset_topology-on-sb-off-sb_fcin0.3_fcout0.1']
    # arch_strings += ['k4_s2_g8_universal_topology-on-cb-off-sb_fcin0.3_fcout0.1']
    # arch_strings += ['k4_s4_wilton_topology-single-wirelength_fcin0.2_fcout0.2']
    # arch_strings += ['k4_s8_wilton_topology-single-wirelength_fcin0.4_fcout0.2']

    # arch_strings += ['k4_s1_subset_topology-single-wirelength_fcin0.6_fcout0.6']
    # arch_strings += ['k4_s1_wilton_topology-single-wirelength_fcin0.6_fcout0.6']
    # arch_strings += ['k4_s1_subset_topology-single-wirelength_fcin0.2_fcout0.4']
    # arch_strings += ['k4_s1_wilton_topology-single-wirelength_fcin0.2_fcout0.4']
    # arch_strings += ['k4_s1_subset_topology-single-wirelength_fcin0.4_fcout0.2']
    # arch_strings += ['k4_s1_wilton_topology-single-wirelength_fcin0.4_fcout0.2']
    # arch_strings += ['k4_s1_subset_topology-single-wirelength_fcin0.3_fcout0.2']
    # arch_strings += ['k4_s1_wilton_topology-single-wirelength_fcin0.3_fcout0.1']
    # arch_strings += ['k4_s1_wilton_topology-single-wirelength_fcin0.7_fcout0.2']
    # arch_strings += ['k4_s1_subset_topology-single-wirelength_fcin0.7_fcout0.2']

    #### 100 random 6LUT architectures ####
    # arch_strings += ['k6_s4_g8_universal_topology-on-cb-off-cb_fcin0.2_fcout0.05']
    # arch_strings += ['k6_s4_wilton_topology-single-wirelength_fcin0.05_fcout0.05']
    # arch_strings += ['k6_s2_wilton_topology-single-wirelength_fcin0.05_fcout0.2']
    # arch_strings += ['k6_s2_subset_topology-single-wirelength_fcin0.2_fcout0.1']
    # arch_strings += ['k6_s4_g16_universal_topology-on-cb-off-cb_fcin0.1_fcout0.1']
    # arch_strings += ['k6_s8_wilton_topology-single-wirelength_fcin0.1_fcout0.4']
    # arch_strings += ['k6_s4_universal_topology-single-wirelength_fcin0.1_fcout0.05']
    # arch_strings += ['k6_s4_universal_topology-single-wirelength_fcin0.6_fcout0.4']
    # arch_strings += ['k6_s4_g8_subset_topology-on-sb-off-sb_fcin0.4_fcout0.05']
    # arch_strings += ['k6_s4_g8_wilton_topology-on-sb-off-sb_fcin0.4_fcout0.6']
    # arch_strings += ['k6_s4_wilton_topology-single-wirelength_fcin0.05_fcout0.4']
    # arch_strings += ['k6_s4_g16_wilton_topology-on-cbsb-off-cbsb_fcin0.6_fcout0.6']
    # arch_strings += ['k6_s1_universal_topology-single-wirelength_fcin0.1_fcout0.6']
    # arch_strings += ['k6_s4_g8_universal_topology-on-cb-off-sb_fcin0.1_fcout0.05']
    # arch_strings += ['k6_s4_wilton_topology-single-wirelength_fcin0.4_fcout0.1']
    # arch_strings += ['k6_s16_subset_topology-single-wirelength_fcin0.1_fcout0.6']
    # arch_strings += ['k6_s8_universal_topology-single-wirelength_fcin0.4_fcout0.1']
    # arch_strings += ['k6_s4_g4_wilton_topology-on-cb-off-sb_fcin0.4_fcout0.6']
    # arch_strings += ['k6_s4_g4_subset_topology-on-cbsb-off-cbsb_fcin0.1_fcout0.1']
    # arch_strings += ['k6_s16_wilton_topology-single-wirelength_fcin0.1_fcout0.1']
    # arch_strings += ['k6_s4_g8_universal_topology-on-cbsb-off-cbsb_fcin0.1_fcout0.6']
    # arch_strings += ['k6_s8_universal_topology-single-wirelength_fcin0.6_fcout0.2']
    # arch_strings += ['k6_s2_universal_topology-single-wirelength_fcin0.1_fcout0.2']
    # arch_strings += ['k6_s8_wilton_topology-single-wirelength_fcin0.4_fcout0.1']
    # arch_strings += ['k6_s2_universal_topology-single-wirelength_fcin0.6_fcout0.6']
    # arch_strings += ['k6_s8_universal_topology-single-wirelength_fcin0.6_fcout0.1']
    # arch_strings += ['k6_s1_subset_topology-single-wirelength_fcin0.2_fcout0.4']
    # arch_strings += ['k6_s4_g16_subset_topology-on-cbsb-off-cbsb_fcin0.1_fcout0.05']
    # arch_strings += ['k6_s4_g16_universal_topology-on-sb-off-sb_fcin0.05_fcout0.4']
    # arch_strings += ['k6_s4_g8_wilton_topology-on-cb-off-sb_fcin0.2_fcout0.05']
    # arch_strings += ['k6_s4_g4_universal_topology-on-cb-off-cb_fcin0.4_fcout0.05']
    # arch_strings += ['k6_s4_wilton_topology-single-wirelength_fcin0.2_fcout0.2']
    # arch_strings += ['k6_s1_subset_topology-single-wirelength_fcin0.2_fcout0.6']
    # arch_strings += ['k6_s2_wilton_topology-single-wirelength_fcin0.2_fcout0.05']
    # arch_strings += ['k6_s4_universal_topology-single-wirelength_fcin0.2_fcout0.6']
    # arch_strings += ['k6_s2_subset_topology-single-wirelength_fcin0.05_fcout0.1']
    # arch_strings += ['k6_s8_wilton_topology-single-wirelength_fcin0.05_fcout0.2']
    # arch_strings += ['k6_s1_universal_topology-single-wirelength_fcin0.4_fcout0.6']
    # arch_strings += ['k6_s4_g8_wilton_topology-on-cbsb-off-cbsb_fcin0.6_fcout0.4']
    # arch_strings += ['k6_s4_g16_universal_topology-on-cbsb-off-cbsb_fcin0.1_fcout0.6']
    # arch_strings += ['k6_s4_subset_topology-single-wirelength_fcin0.6_fcout0.6']
    # arch_strings += ['k6_s4_g4_wilton_topology-on-cb-off-cb_fcin0.2_fcout0.6']
    # arch_strings += ['k6_s8_subset_topology-single-wirelength_fcin0.05_fcout0.2']
    # arch_strings += ['k6_s16_subset_topology-single-wirelength_fcin0.2_fcout0.2']
    # arch_strings += ['k6_s16_wilton_topology-single-wirelength_fcin0.1_fcout0.6']
    # arch_strings += ['k6_s2_universal_topology-single-wirelength_fcin0.05_fcout0.4']
    # arch_strings += ['k6_s2_universal_topology-single-wirelength_fcin0.2_fcout0.4']
    # arch_strings += ['k6_s4_g16_universal_topology-on-cb-off-cb_fcin0.1_fcout0.4']
    # arch_strings += ['k6_s4_g4_universal_topology-on-cbsb-off-cbsb_fcin0.05_fcout0.6']
    # arch_strings += ['k6_s1_subset_topology-single-wirelength_fcin0.4_fcout0.1']
    # arch_strings += ['k6_s1_wilton_topology-single-wirelength_fcin0.05_fcout0.4']
    # arch_strings += ['k6_s4_g8_subset_topology-on-cb-off-cbsb_fcin0.1_fcout0.2']
    # arch_strings += ['k6_s4_g4_universal_topology-on-cb-off-cbsb_fcin0.4_fcout0.6']
    # arch_strings += ['k6_s4_g16_universal_topology-on-cbsb-off-cbsb_fcin0.2_fcout0.2']
    # arch_strings += ['k6_s4_g4_wilton_topology-on-cb-off-sb_fcin0.6_fcout0.2']
    # arch_strings += ['k6_s4_wilton_topology-single-wirelength_fcin0.1_fcout0.6']
    # arch_strings += ['k6_s4_universal_topology-single-wirelength_fcin0.6_fcout0.05']
    # arch_strings += ['k6_s4_g4_universal_topology-on-cb-off-cb_fcin0.6_fcout0.2']
    # arch_strings += ['k6_s4_g16_wilton_topology-on-sb-off-sb_fcin0.6_fcout0.05']
    # arch_strings += ['k6_s4_g4_wilton_topology-on-sb-off-sb_fcin0.05_fcout0.05']
    # arch_strings += ['k6_s4_g8_subset_topology-on-cb-off-cbsb_fcin0.2_fcout0.05']
    # arch_strings += ['k6_s2_wilton_topology-single-wirelength_fcin0.4_fcout0.2']
    # arch_strings += ['k6_s2_universal_topology-single-wirelength_fcin0.6_fcout0.05']
    # arch_strings += ['k6_s4_subset_topology-single-wirelength_fcin0.6_fcout0.05']
    # arch_strings += ['k6_s16_wilton_topology-single-wirelength_fcin0.4_fcout0.4']
    # arch_strings += ['k6_s16_subset_topology-single-wirelength_fcin0.2_fcout0.4']
    # arch_strings += ['k6_s4_g4_subset_topology-on-cb-off-sb_fcin0.2_fcout0.1']
    # arch_strings += ['k6_s16_universal_topology-single-wirelength_fcin0.05_fcout0.05']
    # arch_strings += ['k6_s8_wilton_topology-single-wirelength_fcin0.05_fcout0.4']
    # arch_strings += ['k6_s4_g4_universal_topology-on-sb-off-sb_fcin0.4_fcout0.05']
    # arch_strings += ['k6_s4_g16_subset_topology-on-cb-off-cb_fcin0.4_fcout0.05']
    # arch_strings += ['k6_s4_g4_universal_topology-on-cb-off-cbsb_fcin0.1_fcout0.4']
    # arch_strings += ['k6_s8_subset_topology-single-wirelength_fcin0.2_fcout0.05']
    # arch_strings += ['k6_s4_g8_universal_topology-on-cb-off-cb_fcin0.6_fcout0.2']
    # arch_strings += ['k6_s4_g16_wilton_topology-on-cb-off-cbsb_fcin0.05_fcout0.2']
    # arch_strings += ['k6_s4_g8_subset_topology-on-sb-off-sb_fcin0.05_fcout0.6']
    # arch_strings += ['k6_s8_wilton_topology-single-wirelength_fcin0.6_fcout0.2']
    # arch_strings += ['k6_s4_g16_wilton_topology-on-cbsb-off-cbsb_fcin0.6_fcout0.2']
    # arch_strings += ['k6_s2_universal_topology-single-wirelength_fcin0.1_fcout0.4']
    # arch_strings += ['k6_s8_wilton_topology-single-wirelength_fcin0.05_fcout0.6']
    # arch_strings += ['k6_s4_g8_subset_topology-on-cb-off-cbsb_fcin0.6_fcout0.05']
    # arch_strings += ['k6_s4_g4_subset_topology-on-sb-off-sb_fcin0.4_fcout0.4']
    # arch_strings += ['k6_s2_universal_topology-single-wirelength_fcin0.2_fcout0.6']
    # arch_strings += ['k6_s2_wilton_topology-single-wirelength_fcin0.1_fcout0.6']
    # arch_strings += ['k6_s2_subset_topology-single-wirelength_fcin0.1_fcout0.05']
    # arch_strings += ['k6_s4_g16_universal_topology-on-cb-off-cbsb_fcin0.2_fcout0.2']
    # arch_strings += ['k6_s4_g8_wilton_topology-on-cb-off-sb_fcin0.6_fcout0.1']
    # arch_strings += ['k6_s4_g16_universal_topology-on-cbsb-off-cbsb_fcin0.05_fcout0.05']
    # arch_strings += ['k6_s4_universal_topology-single-wirelength_fcin0.4_fcout0.2']
    # arch_strings += ['k6_s1_wilton_topology-single-wirelength_fcin0.6_fcout0.05']
    # arch_strings += ['k6_s2_wilton_topology-single-wirelength_fcin0.1_fcout0.05']
    # arch_strings += ['k6_s1_subset_topology-single-wirelength_fcin0.05_fcout0.4']
    # arch_strings += ['k6_s4_g8_universal_topology-on-cbsb-off-cbsb_fcin0.05_fcout0.05']
    # arch_strings += ['k6_s4_subset_topology-single-wirelength_fcin0.4_fcout0.4']
    # arch_strings += ['k6_s4_g16_subset_topology-on-cb-off-cbsb_fcin0.4_fcout0.1']
    # arch_strings += ['k6_s16_universal_topology-single-wirelength_fcin0.1_fcout0.4']
    # arch_strings += ['k6_s1_subset_topology-single-wirelength_fcin0.6_fcout0.4']
    # arch_strings += ['k6_s2_universal_topology-single-wirelength_fcin0.6_fcout0.1']
    # arch_strings += ['k6_s4_g8_subset_topology-on-sb-off-sb_fcin0.6_fcout0.05']
    # arch_strings += ['k6_s1_wilton_topology-single-wirelength_fcin0.2_fcout0.6']

    # build a list of arch points based on the arch strings
    for arch_str in arch_strings:
        arch_point = ArchPointInfo.from_str(arch_str)
        arch_list += [arch_point]
        #if arch_point.lut_size != 4:
        #    continue
        #if arch_point.fcin > 0.3 or arch_point.fcout > 0.3:
        #    continue
        #if arch_point.g_wirelength is None:
        #    arch_list += [arch_point]

    return arch_list
