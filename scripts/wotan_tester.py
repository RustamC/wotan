import multiprocessing
import os
import pathlib
import subprocess
import sys
import shutil
from typing import Optional

import numpy as np

import arch_handler as ah
from my_regex import *

# Enums
e_Test_Type = ('normal',
               'binary_search_norm_demand',
               'binary_search_routability_metric'
               )


# returns geometric mean of list
def get_geomean(my_list):
    result = 1.0
    for num in my_list:
        result *= num
    result **= (1.0 / len(my_list))
    return result


# Command-Line Related
# parses the specified string and returns a list of arguments where each
# space-delimited value receives its own entry in the list
def get_argument_list(string):
    result = string.split()
    return result


# runs command with specified arguments and returns the result
# arguments is a list where each individual argument is in it's own entry
# i.e. the -l and -a in "ls -l -a" would each have their own entry in the list
def run_command(command, arguments):
    result = subprocess.check_output([command] + arguments)
    return result


# returns (x,y) index of 'val' in 'my_list'
def index_2d(my_list, val):
    result_x = None
    result_y = None

    for sublist in my_list:
        if val in sublist:
            result_x = my_list.index(sublist)
            result_y = sublist.index(val)
            break

    return result_x, result_y


# returns the number of pairwise comparisons where wotan ordering agrees with vpr ordering. basically match every
# architecture against every other architecture for wotan, and then see if this pairwise odering agrees with VPR. -
# - assumed that architectures are ordered best to worst. first entry is architecture name, second entry is
#   architecture 'score' (min W for VPR)
def compare_wotan_vpr_arch_orderings(wotan_ordering, vpr_ordering, vpr_tolerance=2):
    # Wotan predictions always treated as correct for architectures within specified VPR score tolerance

    # make sure both ordered lists are the same size
    if len(wotan_ordering) != len(vpr_ordering):
        print('expected wotan and vpr ordered list to be the same size')
        sys.exit()

    total_cases = 0
    agree_cases = 0
    agree_within_tolerance = 0

    i = 0
    while i < len(wotan_ordering) - 1:
        j = i + 1
        while j < len(wotan_ordering):
            arch_one = wotan_ordering[i][0]
            arch_two = wotan_ordering[j][0]

            # now get the index of these two arch points in the vpr ordered list. since the lists are sorted from
            # best to worst, a lower index means a better architecture
            vpr_ind_one, dummy = index_2d(vpr_ordering, arch_one)
            vpr_ind_two, dummy = index_2d(vpr_ordering, arch_two)

            vpr_score_one = float(vpr_ordering[vpr_ind_one][1])
            vpr_score_two = float(vpr_ordering[vpr_ind_two][1])

            if vpr_ind_one < vpr_ind_two:
                agree_cases += 1
                agree_within_tolerance += 1
            elif abs(vpr_score_one - vpr_score_two) <= vpr_tolerance:
                agree_within_tolerance += 1
            else:
                print('Disagreed with VPR ordering:\t' + vpr_ordering[vpr_ind_one][0] + ' (' + str(
                    vpr_score_one) + ') VS ' + vpr_ordering[vpr_ind_two][0] + ' (' + str(vpr_score_two) + ')')

            total_cases += 1
            j += 1

        i += 1

    return agree_cases, agree_within_tolerance, total_cases


# Main class used to run wotan tests
class WotanTester:

    def __init__(self, path: str, arch_path: str, run_path: str, nodisp: bool, threads: int,
                 max_connection_length: int):
        self.path = path
        self.arch_path = arch_path
        self.run_path = run_path
        self.nodisp = nodisp
        self.threads = threads
        self.max_connection_length = max_connection_length
        self.rr_graph = None
        self.demand_multiplier = None
        self.fc_in = 1.0
        self.fc_out = 1.0
        self.build_dir = self.path + '/build'

    def set_fc_in(self, fc_in: float):
        self.fc_in = fc_in

    def set_fc_out(self, fc_out: float):
        self.fc_out = fc_out

    def get_fc_in(self):
        return self.fc_in

    def get_fc_out(self):
        return self.fc_out

    def set_arch_path(self, path: str):
        self.arch_path = path

    def get_arch_path(self):
        return self.arch_path

    def set_run_path(self, path: str):
        self.run_path = path

    def get_run_path(self):
        return self.run_path

    def set_no_disp(self, nodisp: bool):
        self.nodisp = nodisp

    def get_no_disp(self):
        return self.nodisp

    def set_max_connection_length(self, max_connection_length: int):
        self.max_connection_length = max_connection_length

    def get_max_connection_length(self):
        return self.max_connection_length

    def set_demand_multiplier(self, demand_multiplier: Optional[int] = None):
        self.demand_multiplier = demand_multiplier

    def get_demand_multiplier(self):
        return self.demand_multiplier

    def set_rr_graph(self, rr_graph: str):
        suffix = pathlib.Path(rr_graph).suffix
        if suffix == '.xml':
            self.rr_graph = rr_graph
        else:
            raise Exception('Wotan: rr_graph is not xml: ' + rr_graph + '!')

    def get_rr_graph(self):
        return self.rr_graph

    # returns 3-tuple: (final target value, final demand multiplier, wotan output)
    def search_for_demand_multiplier(self, test_type,
                                     target=None,
                                     target_tolerance=None,
                                     target_regex=None,
                                     demand_mult_low=0.0,
                                     demand_mult_high=10,
                                     max_tries=30):

        if self.demand_multiplier is not None:
            print(
                '-demand_multiplier option already included in wotan_opts -- can\'t do binary search for pin demand')
            sys.exit()

        # true if increasing, false if decreasing
        monotonic_increasing = True
        # what we're searching for in wotan output
        if test_type == 'binary_search_norm_demand':
            if not target_regex:
                target_regex = '.*Normalized demand: (\d+\.\d+).*'
            if not target:
                target = 0.8
            if not target_tolerance:
                target_tolerance = 0.01
        elif test_type == 'binary_search_routability_metric':
            if not target_regex:
                target_regex = '.*Routability metric: (\d+\.*\d*).*'
            if not target:
                target = 0.3
            if not target_tolerance:
                target_tolerance = 0.02
            monotonic_increasing = False
        else:
            print('unexpected test_type passed-in to binary search: ' + test_type)
            sys.exit()

        current = 0
        wotan_out = ''

        demand_mult_current = None

        # perform binary search
        try_num = 1
        while abs(current - target) > target_tolerance:
            if try_num > max_tries:
                if current < target:
                    # the architecture is probably very unroutable and it simply can't get to the specified target value
                    print('\t\tarchitecture looks too unroutable; can\'t meet binary search target of ' + str(
                        target) + '. Returning.')
                    break
                else:
                    print('WARNING! Binary search has taken more than ' + str(
                        max_tries) + ' tries to binary search for correct pin demand. using last value...')
                    break
                # sys.exit()

            # get next value of pin demand to try
            demand_mult_current = (demand_mult_high + demand_mult_low) / 2

            self.set_demand_multiplier(demand_mult_current)

            # run wotan and get the value of the target metric
            wotan_out = self.run()
            regex_val = regex_last_token(wotan_out, target_regex)
            current = float(regex_val)

            if monotonic_increasing:
                if current < target:
                    demand_mult_low = demand_mult_current
                else:
                    demand_mult_high = demand_mult_current
            else:
                if current > target:
                    demand_mult_low = demand_mult_current
                else:
                    demand_mult_high = demand_mult_current

            print('\tat demand mult ' + str(demand_mult_current) + ' current val is ' + str(current))
            sys.stdout.flush()

            if demand_mult_low > demand_mult_high:
                print('low value > high value in binary search!')
                sys.exit()

            try_num += 1

        if demand_mult_current is None:
            print('Binary search is not performed!')
            sys.exit()

        return current, demand_mult_current, wotan_out

    def make(self):
        if os.path.exists(self.build_dir):
            shutil.rmtree(self.build_dir)

        os.mkdir(self.build_dir)
        os.chdir(self.build_dir)

        run_command('cmake', ['-DCMAKE_BUILD_TYPE=Release', '..'])
        run_command('make', ['-j4'])

    def get_arguments_string(self):
        arguments = ''
        if self.rr_graph is not None:
            arguments += '-rr_graph_file ' + self.rr_graph + ' '
        else:
            raise Exception('Wotan: rr_graph is not set!')

        arguments += '-threads ' + str(self.threads) + ' '
        if self.demand_multiplier is not None:
            arguments += '-demand_multiplier ' + str(self.demand_multiplier) + ' '

        arguments += '-max_connection_length ' + str(self.max_connection_length) + ' '
        if self.nodisp:
            arguments += '-nodisp '

        arguments += '-fc_in ' + str(self.fc_in) + ' -fc_out ' + str(self.fc_out) + ' '

        return arguments

    def run(self):
        arguments = self.get_arguments_string()
        arg_list = get_argument_list(arguments)

        # switch to testing directory
        os.chdir(self.run_path)

        exe = self.build_dir + '/wotan'
        output = str(run_command(exe, arg_list))
        return output


# Main class used to run wotan tests
class VtrTester:

    def __init__(self, path, run_path, nodisp, threads):
        self.path = path
        self.run_path = run_path
        self.nodisp = nodisp
        self.threads = threads
        self.arch = None
        self.benchmark = None
        self.rr_graph = None
        self.chan_width = None
        self.build_dir = self.path + '/build'
        self.seed = 0
        self.timing_analysis = False

    def set_run_path(self, path):
        self.run_path = path

    def get_run_path(self):
        return self.run_path

    def set_timing_analysis(self, ta: bool):
        self.timing_analysis = ta

    def set_seed(self, seed: int):
        self.seed = seed

    def set_chan_width(self, chan_width: int):
        if chan_width <= 0:
            raise Exception('Channel width is < 0')
        self.chan_width = chan_width

    def get_chan_width(self):
        return self.chan_width

    def set_rr_graph(self, rr_graph: str):
        suffix = pathlib.Path(rr_graph).suffix
        if suffix == '.xml':
            self.rr_graph = rr_graph
        else:
            raise Exception('Wotan: rr_graph is not xml: ' + rr_graph + '!')

    def get_rr_graph(self):
        return self.rr_graph

    def set_benchmark(self, benchmark: str):
        self.benchmark = benchmark
        directory = pathlib.Path(self.benchmark).stem
        self.run_path = self.run_path + '/' + directory

    def get_benchmark(self):
        return self.benchmark

    def is_verilog_benchmark(self):
        suffix = pathlib.Path(self.benchmark).suffix
        if suffix == '.v':
            return True
        elif suffix == '.blif':
            return False
        else:
            raise Exception('VTR: Unknown benchmark type: ' + self.benchmark)

    def set_arch(self, arch: str):
        self.arch = arch

    def get_arch(self):
        return self.arch

    def set_nodisp(self, nodisp: bool):
        self.nodisp = nodisp

    def make(self):
        os.mkdir(self.build_dir)
        os.chdir(self.path)

        run_command('make', ['-j4'])

    def get_arguments_string(self):
        arguments = ''

        benchmark_argument = ''
        if self.benchmark is not None:
            benchmark_argument += self.benchmark + ' '
        else:
            raise Exception('VTR: benchmark is not set!')

        arch_argument = ''
        if self.arch is not None:
            arch_argument += self.arch + ' '
        else:
            raise Exception('VTR: arch is not set!')

        if self.is_verilog_benchmark():
            arguments += benchmark_argument + arch_argument
        else:
            arguments += arch_argument + benchmark_argument

        if self.rr_graph is not None:
            arguments += '--write_rr_graph ' + self.rr_graph + ' '

        if self.nodisp:
            arguments += '--disp off '
        else:
            arguments += '--disp on '

        arguments += '--pack --place '

        arguments += '--timing_analysis on '
        # if self.timing_analysis:
        #     arguments += '--timing_analysis on '
        # else:
        #     arguments += '--timing_analysis off '

        arguments += '--seed ' + str(self.seed) + ' '

        if self.chan_width is None:
            arguments += '--route --router_initial_timing lookahead --router_lookahead map --verify_binary_search on '
            arguments += '--routing_failure_predictor off '
            # arguments += '--route --router_initial_timing lookahead --router_lookahead map '
            # arguments += '--route '
        else:
            arguments += '--route_chan_width ' + str(self.chan_width) + ' '

        if self.is_verilog_benchmark():
            arguments += '-temp_dir ' + self.get_run_path()

        return arguments

    def get_exe_path(self):
        if self.is_verilog_benchmark():
            exe = self.path + '/vtr_flow/scripts/run_vtr_flow.py'
        else:
            exe = self.path + '/vpr/vpr'

        return exe

    def run(self):
        arguments = self.get_arguments_string()
        arg_list = get_argument_list(arguments)

        # switch to testing directory
        if os.path.exists(self.run_path):
            shutil.rmtree(self.run_path)

        os.mkdir(self.run_path)
        os.chdir(self.run_path)

        exe = self.get_exe_path()
        output = str(run_command(exe, arg_list))
        return output


# class used for passing info in multithreading VPR benchmark runs
class VtrBenchmarkInfo:
    def __init__(self, new_tester: VtrTester,
                 benchmark_list,
                 regex_list
                 ):
        self.tester = new_tester
        self.benchmark_list = benchmark_list
        self.regex_list = regex_list


# Main class used to run all tests (including VTR)
class Tester:

    def __init__(self, vtr_tester: VtrTester, wotan_tester: WotanTester, test_type: str):

        self.wotan_tester = wotan_tester
        self.vtr_tester = vtr_tester
        self.test_type = test_type

    def make_vtr(self):
        self.vtr_tester.make()

    def run_vtr(self):
        return self.vtr_tester.run()

    def make_wotan(self):
        self.wotan_tester.make()

    def run_wotan(self):
        return self.wotan_tester.run()

    def get_vtr_simple_benchmarks(self):
        # list of benchmark names
        benchmarks = [
            'alu4',
            'apex2',
            'apex4',
            'des',
            'elliptic',
            'seq',
            's38417',
            'clma'
        ]

        suffix = '.blif'
        bm_dir = '/vtr_flow/benchmarks/blif/'

        # add blif suffix
        benchmarks = [bm + suffix for bm in benchmarks]

        # add full path as prefix
        bm_path = self.vtr_tester.path + bm_dir
        benchmarks = [bm_path + bm for bm in benchmarks]

        return benchmarks

    def get_vtr_verilog_benchmarks(self, lut_size=6):
        # list of benchmark names
        benchmarks = [
            #'bgm',
            'blob_merge',
            # 'boundtop',
            # 'mkDelayWorker32B',
            # 'LU8PEEng',
            # 'mcml',
            # 'stereovision2',
            # 'LU32PEEng',
            # 'mkSMAdapter4B',
            # 'or1200',
            'raygentop',
            'sha'
            #,
            # 'stereovision0',
            # 'stereovision1'
        ]

        suffix = '.v'
        bm_dir = '/vtr_flow/benchmarks/verilog/'

        # add blif suffix
        benchmarks = [bm + suffix for bm in benchmarks]

        # add full path as prefix
        bm_path = self.vtr_tester.path + bm_dir
        benchmarks = [bm_path + bm for bm in benchmarks]

        return benchmarks

    def get_vtr_benchmarks(self, lut_size=6):
        # list of benchmark names
        benchmarks = [
            'bgm',
            'blob_merge',
            'boundtop',
            #'mkDelayWorker32B',
            # 'LU8PEEng',
            # 'mcml',
            # 'stereovision2',
            # 'LU32PEEng',
            # 'mkSMAdapter4B',
            'or1200',
            'raygentop',
            'sha'
            #,
            'stereovision0',
            'stereovision1'
        ]

        suffix = '.pre-vpr.blif'
        bm_dir = '/vtr_flow/benchmarks/6LUT_vtr_benchmarks_blif/'

        if lut_size == 4:
            bm_dir = '/vtr_flow/benchmarks/4LUT_DSP_vtr_benchmarks_blif/'

        # add blif suffix
        benchmarks = [bm + suffix for bm in benchmarks]

        # add full path as prefix
        bm_path = self.vtr_tester.path + bm_dir
        benchmarks = [bm_path + bm for bm in benchmarks]

        return benchmarks

    # runs provided list of benchmarks and returns outputs (based on regex_list) averaged over the specified list of
    # seeds. this function basically calls 'run_vpr_benchmarks' for each seed in the list
    def run_vpr_benchmarks_multiple_seeds(self, benchmark_list,
                                          regex_list, vpr_arch, arch_point,
                                          vpr_seed_list=None,  # by default run with single seed
                                          num_threads=1):  # by default run with 1 thread
        if vpr_seed_list is None:
            vpr_seed_list = [1]
        result_table = []

        if num_threads > len(benchmark_list):
            num_threads = len(benchmark_list)

        # run vpr benchmarks for each specified seed
        for seed in vpr_seed_list:
            print('SEED ' + str(seed) + ' of ' + str(len(vpr_seed_list)))
            seed_result = self.run_vpr_benchmarks(benchmark_list, regex_list, vpr_arch, arch_point,
                                                  seed, num_threads=num_threads)

            result_table += [seed_result]

        # take average of all results
        result_table = np.array(result_table)

        avg_results = []
        for column in result_table.T:
            column_avg = sum(column) / float(len(column))
            avg_results += [column_avg]

        return avg_results

    # runs provided list of benchmarks and returns geomean outputs based on the provided list of regular expressions
    def run_vpr_benchmarks(self, benchmark_list,
                           regex_list, arch_path, arch_point,
                           vpr_seed=1,  # default seed of 1
                           num_threads=1):  # number of concurrent VPR executables to run

        # make 2-d list into which results of each benchmark run will go
        outputs = []
        for _ in regex_list:
            # an entry for each regex
            outputs += [[]]

        # self.change_vpr_rr_struct_dump(self.vpr_path, enable=False)
        # self.make_vtr()

        # create a temporary directory for each benchmark to store the vpr executable (otherwise many threads try to
        # write to the same vpr output file)
        temp_dir = self.vtr_tester.path + '/script_temp_vtr' + '_' + str(vpr_seed) + '/' + arch_point.arch_string
        # cleanup temp directory if it already exists
        if os.path.isdir(temp_dir):
            shutil.rmtree(temp_dir)

        pathlib.Path(temp_dir).mkdir(parents=True, exist_ok=True)

        # multithread vpr runs
        iterables = []
        for bm in benchmark_list:
            # VPR should be run with the -nodisp option and some seed
            new_tester = VtrTester(self.vtr_tester.path, None, True, 1)
            new_tester.set_nodisp(True)
            new_tester.set_timing_analysis(False)
            new_tester.set_seed(vpr_seed)

            index = benchmark_list.index(bm)
            bm_dir = 'bm' + str(index)
            bm_dir = os.path.join(temp_dir, bm_dir)
            os.mkdir(bm_dir)
            
            try:
                new_arch_path = shutil.copy(arch_path, bm_dir)
            except OSError as err:
                print(err)
                sys.exit(1)

            if os.path.isfile(new_arch_path) is False:
                print(new_arch_path + ' doesnt exist!')
                sys.exit(0)

            suffix = pathlib.Path(arch_path).suffix
            arch_name = os.path.basename(arch_path)
            if '.xml' != suffix:
                print('Tester: non-XML arch name: ' + arch_name)
                raise

            # new_arch_path = bm_dir + '/' + arch_name
            # new_vpr_path = bm_dir + '/vpr'

            new_tester.set_run_path(bm_dir)
            new_tester.set_arch(new_arch_path)
            new_tester.set_benchmark(bm)

            iterables += [VtrBenchmarkInfo(new_tester, benchmark_list, regex_list)]

        os.system("taskset -p 0xffffffff %d" % os.getpid())
        mp_pool = multiprocessing.Pool(processes=num_threads)
        try:
            outputs = mp_pool.map(run_vpr_benchmark, iterables)
            mp_pool.close()
            mp_pool.join()
        except KeyboardInterrupt:
            print('Caught KeyboardInterrupt. Terminating threads and exiting.')
            mp_pool.terminate()
            mp_pool.join()
            sys.exit()

        outputs = np.array(outputs)

        # return geomean for each column (?) in the outputs table
        geomean_outputs = []
        for regex in regex_list:
            ind = regex_list.index(regex)
            benchmarks_result_list = outputs[:, ind].tolist()
            for out in benchmarks_result_list:
                print('\t\tbenchmark %d routed at W=%d' % (benchmarks_result_list.index(out), int(out)))
                sys.stdout.flush()

            geomean_outputs += [get_geomean(benchmarks_result_list)]

        return geomean_outputs

    def wrun_fast(self, arch_list, results_file, demand):

        print("Evaluating architecture list (fast mode) ...")

        # specifies how architectures should be evaluated.
        # binary search over pin demand until target prob is hit with specified tolerance
        target_regex = '.*Routability metric: (\d+\.*\d*).*'

        # a list of channel widths over which to evaluate w/ wotan (i.e. geomean)
        chan_widths = [100]
        wotan_results = []

        # for each architecture point:
        #   - evaluate with wotan
        #   - evaluate with VPR if enabled
        for arch_point in arch_list:
            arch_point_index = arch_list.index(arch_point)
            print('Run ' + str(arch_point_index + 1) + '/' + str(len(arch_list)) + '    arch is ' + arch_point.as_str())

            # path to architecture
            wotan_arch_path = get_path_to_arch(self.wotan_tester.get_arch_path(), arch_point)
            print('Path to arch: ' + wotan_arch_path)

            # Evaluate architecture with Wotan
            metric_value_list = []
            for chanw in chan_widths:
                print('W = ' + str(chanw))

                if arch_point.lut_size == 4:
                    benchmark = '4LUT_DSP_vtr_benchmarks_blif/sha.pre-vpr.blif'
                else:
                    benchmark = '6LUT_vtr_benchmarks_blif/sha.pre-vpr.blif'
                # benchmark = 'verilog/sha.v'
                self.vtr_tester.set_chan_width(chanw)
                self.vtr_tester.set_rr_graph('dumped_rr_graph.xml')
                self.vtr_tester.set_benchmark(self.vtr_tester.path + '/vtr_flow/benchmarks/' + benchmark)
                self.vtr_tester.set_arch(wotan_arch_path)
                self.run_vtr()

                self.wotan_tester.set_rr_graph(self.vtr_tester.get_run_path() + '/dumped_rr_graph.xml')
                self.wotan_tester.set_fc_in(arch_point.fcin)
                self.wotan_tester.set_fc_out(arch_point.fcout)
                self.wotan_tester.set_demand_multiplier(demand)

                wotan_out = self.wotan_tester.run()

                metric_regex = target_regex
                # metric_label = 'Demand Multiplier'
                metric_value_list += [float(regex_last_token(wotan_out, metric_regex))]

                # add metric to list of wotan results
            metric_value = get_geomean(metric_value_list)
            print('geomean score: ' + str(metric_value))
            wotan_result_entry = [arch_point_index, arch_point.as_str(), metric_value]
            wotan_results += [wotan_result_entry]

        wotan_results.sort(key=lambda x: x[2], reverse=True)

        with open(results_file, 'w+') as f:
            for w_result in wotan_results:
                result_index = wotan_results.index(w_result)

                for w_elem in w_result:
                    f.write(str(w_elem) + '\t')
                f.write('\n')

    def wrun(self, arch_list, results_file):
    
        print("Evaluating architecture list...")

        # specifies how architectures should be evaluated.
        # binary search over pin demand until target prob is hit with specified tolerance
        target_prob = 0.5
        target_tolerance = 0.0099
        target_regex = '.*Routability metric: (\d+\.*\d*).*'

        # a list of channel widths over which to evaluate w/ wotan (i.e. geomean)
        chan_widths = [100]
        wotan_results = []

        # for each architecture point:
        #   - evaluate with wotan
        #   - evaluate with VPR if enabled
        for arch_point in arch_list:
            arch_point_index = arch_list.index(arch_point)
            print('Run ' + str(arch_point_index + 1) + '/' + str(len(arch_list)) + '    arch is ' + arch_point.as_str())

            # path to architecture
            wotan_arch_path = get_path_to_arch(self.wotan_tester.get_arch_path(), arch_point)
            new_path = self.vtr_tester.path + '/archs' + '/' + arch_point.as_str()
            pathlib.Path(new_path).mkdir(parents=True, exist_ok=True)
            wotan_arch_path = shutil.copy(wotan_arch_path, new_path)
            print('Path to arch: ' + wotan_arch_path)

            # Evaluate architecture with Wotan
            metric_value_list = []
            for chanw in chan_widths:
                print('W = ' + str(chanw))

                if arch_point.lut_size == 4:
                    benchmark = '4LUT_DSP_vtr_benchmarks_blif/sha.pre-vpr.blif'
                else:
                    benchmark = '6LUT_vtr_benchmarks_blif/sha.pre-vpr.blif'
                # benchmark = 'verilog/sha.v'
                self.vtr_tester.set_chan_width(chanw)
                self.vtr_tester.set_rr_graph('dumped_rr_graph.xml')
                self.vtr_tester.set_benchmark(self.vtr_tester.path + '/vtr_flow/benchmarks/' + benchmark)
                self.vtr_tester.set_arch(wotan_arch_path)
                self.run_vtr()

                self.wotan_tester.set_rr_graph(self.vtr_tester.get_run_path() + '/dumped_rr_graph.xml')
                self.wotan_tester.set_fc_in(arch_point.fcin)
                self.wotan_tester.set_fc_out(arch_point.fcout)

                # run binary search to find pin demand at which the target_regex hits its target value
                (target_val, demand_mult, wotan_out) = self.wotan_tester.search_for_demand_multiplier(
                    test_type=self.test_type,
                    target=target_prob,
                    target_tolerance=target_tolerance,
                    target_regex=target_regex,
                    demand_mult_high=200,
                    max_tries=30)
                # get metric used for evaluating the architecture
                self.wotan_tester.set_demand_multiplier()
                # TODO: put this value into arch point info based on test suites? don't want to be hard-coding...
                metric_regex = '.*Demand multiplier: (\d*\.*\d+).*'
                # metric_label = 'Demand Multiplier'
                metric_value_list += [float(regex_last_token(wotan_out, metric_regex))]

            # add metric to list of wotan results
            metric_value = get_geomean(metric_value_list)
            print('geomean score: ' + str(metric_value))
            wotan_result_entry = [arch_point_index, arch_point.as_str(), metric_value]
            wotan_results += [wotan_result_entry]

        wotan_results.sort(key=lambda x: x[2], reverse=True)

        with open(results_file, 'w+') as f:
            for w_result in wotan_results:
                result_index = wotan_results.index(w_result)

                for w_elem in w_result:
                    f.write(str(w_elem) + '\t')
                f.write('\n')

    def vtr_run_fast(self, arch_list, results_file):
        print("Evaluating architecture list with VPR...")

        run_vpr_comparisons = False
        vpr_evaluation_seeds = [0, 1, 2]

        vpr_results = []

        for arch_point in arch_list:
            arch_point_index = arch_list.index(arch_point)
            print('Run ' + str(arch_point_index + 1) + '/' + str(len(arch_list)) + '    arch is ' + arch_point.as_str())

            # path to architecture
            wotan_arch_path = get_path_to_arch(self.wotan_tester.get_arch_path(), arch_point)

            new_path = self.vtr_tester.path + '/archs' + '/' + arch_point.as_str()
            pathlib.Path(new_path).mkdir(parents=True, exist_ok=True)
            wotan_arch_path = shutil.copy(wotan_arch_path, new_path)
            print("Evaluating with vpr now...")

            # what regex / benchmarks to run?
            vpr_regex_list = ['channel width factor of (\d+)']
            benchmarks  = self.get_vtr_benchmarks(lut_size=arch_point.lut_size)
            benchmarks += self.get_vtr_simple_benchmarks()


            results = self.run_vpr_benchmarks_multiple_seeds(benchmarks, vpr_regex_list, wotan_arch_path, arch_point,
                                                             vpr_seed_list=vpr_evaluation_seeds,
                                                             num_threads=3)
            # add VPR result to running list
            print(arch_point.as_str() + ' result is: ' + str(results[0]))

            vpr_result_entry = [arch_point_index, arch_point.as_str(), results[0]]
            vpr_results += [vpr_result_entry]

            vpr_results.sort(key=lambda x: x[2])

            with open(results_file, 'w+') as f:
                for vpr_result in vpr_results:
                    f.write(str(vpr_result) + '\t')
                    f.write('\n')

                f.write('\n')

    # evaluates routability of each architecture point in the specified list (optionally runs VPR on this list as well).
    # results are written in table form to the specified file
    #    wotan results are sorted best to worst
    #    VPR results, if enabled, are sorter best to worst (in terms on channel width)
    def run(self, arch_list, results_file, vpr_arch_ordering=None):
        print("Evaluating architecture list...")

        run_vpr_comparisons = False
        if vpr_arch_ordering is None:
            vpr_arch_ordering = []
            run_vpr_comparisons = True

        # specifies how architectures should be evaluated.
        # binary search over pin demand until target prob is hit with specified tolerance
        target_prob = 0.5
        target_tolerance = 0.000099
        target_regex = '.*Routability metric: (\d+\.*\d*).*'

        # a list of channel widths over which to evaluate w/ wotan (i.e. geomean)
        chan_widths = [100]
        vpr_evaluation_seeds = [0, 1, 2]

        wotan_results = []
        vpr_results = []

        # for each architecture point:
        #   - evaluate with wotan
        #   - evaluate with VPR if enabled
        for arch_point in arch_list:
            arch_point_index = arch_list.index(arch_point)
            print('Run ' + str(arch_point_index + 1) + '/' + str(len(arch_list)) + '    arch is ' + arch_point.as_str())

            # path to architecture
            wotan_arch_path = get_path_to_arch(self.wotan_tester.get_arch_path(), arch_point)

            new_path = self.vtr_tester.path + '/archs' + '/' + arch_point.as_str()
            pathlib.Path(new_path).mkdir(parents=True, exist_ok=True)
            wotan_arch_path = shutil.copy(wotan_arch_path, new_path)

            # Evaluate architecture with Wotan
            metric_value_list = []
            for chanw in chan_widths:
                print('W = ' + str(chanw))

                if arch_point.lut_size == 4:
                    benchmark = '4LUT_DSP_vtr_benchmarks_blif/sha.pre-vpr.blif'
                else:
                    benchmark = '6LUT_vtr_benchmarks_blif/sha.pre-vpr.blif'
                #benchmark = 'verilog/sha.v'
                self.vtr_tester.set_chan_width(chanw)
                self.vtr_tester.set_rr_graph('dumped_rr_graph.xml')
                self.vtr_tester.set_benchmark(self.vtr_tester.path + '/vtr_flow/benchmarks/' + benchmark)
                self.vtr_tester.set_arch(wotan_arch_path)
                self.run_vtr()

                self.wotan_tester.set_rr_graph(self.vtr_tester.get_run_path() + '/dumped_rr_graph.xml')

                # run binary search to find pin demand at which the target_regex hits its target value
                (target_val, demand_mult, wotan_out) = self.wotan_tester.search_for_demand_multiplier(
                    test_type=self.test_type,
                    target=target_prob,
                    target_tolerance=target_tolerance,
                    target_regex=target_regex,
                    demand_mult_high=200,
                    max_tries=30)
                # get metric used for evaluating the architecture
                self.wotan_tester.set_demand_multiplier()
                # TODO: put this value into arch point info based on test suites? don't want to be hard-coding...
                metric_regex = '.*Demand multiplier: (\d*\.*\d+).*'
                # metric_label = 'Demand Multiplier'
                metric_value_list += [float(regex_last_token(wotan_out, metric_regex))]

            # add metric to list of wotan results
            metric_value = get_geomean(metric_value_list)
            print('geomean score: ' + str(metric_value))
            wotan_result_entry = [arch_point_index, arch_point.as_str(), metric_value]
            wotan_results += [wotan_result_entry]

            # Evaluate architecture with VPR
            if run_vpr_comparisons:
                print("Evaluating with vpr now...")

                # what regex / benchmarks to run?
                vpr_regex_list = ['channel width factor of (\d+)']
                benchmarks = self.get_vtr_simple_benchmarks(lut_size=arch_point.lut_size)
                
                results = self.run_vpr_benchmarks_multiple_seeds(benchmarks, vpr_regex_list, wotan_arch_path, arch_point,
                                                                 vpr_seed_list=vpr_evaluation_seeds,
                                                                 num_threads=3)
                # add VPR result to running list
                vpr_result_entry = [arch_point_index, arch_point.as_str(), results[0]]
                vpr_results += [vpr_result_entry]

        # sort results -- descending for wotan, ascending for vpr
        wotan_results.sort(key=lambda x: x[2], reverse=True)
        vpr_results.sort(key=lambda x: x[2])

        try:
            # figure out how many pairwise comparisons of wotan agree with VPR
            # --> compare every architecture result to every other architecture result
            agree_cases = 0
            agree_within_tolerance = 0
            total_cases = 0
            vpr_tolerance = 2
            wotan_arch_ordering = [el[1:3] for el in
                                   wotan_results]  # get arch string and score for each element in 'wotan_arch_ordering'
            if run_vpr_comparisons:
                vpr_arch_ordering = [el[1:3] for el in vpr_results]

                [agree_cases, agree_within_tolerance, total_cases] = compare_wotan_vpr_arch_orderings(
                    wotan_arch_ordering, vpr_arch_ordering, vpr_tolerance)
            else:
                # compare wotan results against passed-in list
                if len(wotan_arch_ordering) == len(vpr_arch_ordering):
                    [agree_cases, agree_within_tolerance, total_cases] = compare_wotan_vpr_arch_orderings(
                        wotan_arch_ordering, vpr_arch_ordering, vpr_tolerance)
        except TypeError as e:
            print('caught exception:')
            print(e)
            print('continuing anyway')

        with open(results_file, 'w+') as f:
            for w_result in wotan_results:
                result_index = wotan_results.index(w_result)

                if run_vpr_comparisons:
                    v_result = vpr_results[result_index]
                else:
                    v_result = []

                for w_elem in w_result:
                    f.write(str(w_elem) + '\t')
                f.write('\t')
                for v_elem in v_result:
                    f.write(str(v_elem) + '\t')
                f.write('\n')

            f.write('\n')
            f.write('Wotan and VPR agree in ' + str(agree_cases) + '/' + str(total_cases) + ' pairwise comparisons\n')
            f.write(str(agree_within_tolerance) + '/' + str(
                total_cases) + ' cases agree within VPR minW tolerance of ' + str(vpr_tolerance))


# runs specified vpr benchmark and returns regex'd outputs in a list
def run_vpr_benchmark(bm_info: VtrBenchmarkInfo):
    tester: VtrTester = bm_info.tester
    benchmark_list = bm_info.benchmark_list
    regex_list = bm_info.regex_list

    output_list = []

    try:
        vpr_out = str(tester.run())
    except KeyboardInterrupt:
        # dealing with python 2.7 compatibility stupidness... i can't get multiprocessing to terminate on "ctrl-c"
        # unless I write this try-except statement. and even then I have to bang on ctrl-c repeatedly to get the
        # desired effect :(
        print('worker received interrupt. exiting.')
        return
    except subprocess.CalledProcessError:
        print('Benchmark is not routable in FPGA (for more info look for log): running at ' + tester.get_run_path() + ', benchmark: ' + tester.get_benchmark())
        w = 1000.0
        print('Setting W = ' + str(w))
        for regex in regex_list:
            output_list += [w]

        ind = benchmark_list.index(tester.get_benchmark())
        print('\t\tbenchmark: ' + str(ind) + ' done')
        return output_list


    # parse outputs according to user's regex list
    for regex in regex_list:
        # ind = regex_list.index(regex)
        parsed = float(regex_last_token(vpr_out, regex))
        output_list += [parsed]

    ind = benchmark_list.index(tester.get_benchmark())
    print('\t\tbenchmark: ' + str(ind) + ' done')
    # print('\t\t\tvpr opts: ' + vpr_opts)
    return output_list


# just a wrapper for the function of the same name in arch_handler.py
def get_path_to_arch(arch_base, arch_point):
    sb_pattern = arch_point.switchblock_pattern
    wire_topology = arch_point.wire_topology
    wirelengths = {'semi-global': arch_point.s_wirelength}
    if arch_point.g_wirelength is not None:
        wirelengths['global'] = arch_point.g_wirelength
    global_via_repeat = 4
    fc_in = arch_point.fcin
    fc_out = arch_point.fcout
    lut_size = str(arch_point.lut_size) + 'LUT'

    arch_path = ah.get_path_to_arch(arch_base, sb_pattern, wire_topology, wirelengths, global_via_repeat, fc_in, fc_out,
                                    lut_size)

    return arch_path
