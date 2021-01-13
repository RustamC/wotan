import time

import arch_points
import wotan_tester as wt

# Init paths
base_path = '/home/chochaev_r/src'
vtr_path = base_path + '/vtr-verilog-to-routing'
wotan_path = base_path + '/wotan'
arch_path = wotan_path + '/arch'
testing_path_suffix = '/testing'

# Init wotan tester
wotan_tester = wt.WotanTester(path=wotan_path, arch_path=arch_path, run_path=wotan_path + testing_path_suffix,
                              nodisp=True, threads=25, max_connection_length=8)

vtr_tester = wt.VtrTester(path=vtr_path, run_path=vtr_path + testing_path_suffix, nodisp=True, threads=1)

test_type = 'binary_search_routability_metric'
tester = wt.Tester(vtr_tester, wotan_tester, test_type)

# Run Tests
start_time = time.time()

# Get list of architecture points
arch_list = arch_points.get_custom_arch_list()

# Get absolute metric for a list of architecture points


vtr_run = False
# VTR testing
if vtr_run is True:
    the_arch = arch_list[0].as_str()
    result_file = wotan_path + testing_path_suffix + '/vtr_' + the_arch + '.txt'
    tester.vtr_run_fast(arch_list, result_file)
else:
    result_file = wotan_path + testing_path_suffix + '/wotan_4LUT_last_try.txt'
    tester.wrun(arch_list, result_file)
#result_file = wotan_path + testing_path_suffix + '/wotan_4LUT_simple.txt'
#tester.run(arch_list, result_file, None)
#tester.wrun(arch_list, result_file)
#tester.wrun_fast(arch_list, result_file, 0.3)


# Finish
end_time = time.time()
print('Done. Took ' + str(round(end_time - start_time, 3)) + ' seconds')
