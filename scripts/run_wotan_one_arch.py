import time

import arch_points
import wotan_tester as wt
import arch_handler as ah

# Init paths
base_path = '/home/chochaev_r/src'
vtr_path = base_path + '/vtr-verilog-to-routing'
wotan_path = base_path + '/wotan'
arch_path = wotan_path + '/arch'
testing_path_suffix = '/testing'

# Init wotan tester
wotan_tester = wt.WotanTester(path=wotan_path, arch_path=arch_path, run_path=wotan_path + testing_path_suffix,
                              nodisp=True, threads=8, max_connection_length=2)

vtr_tester = wt.VtrTester(path=vtr_path, run_path=vtr_path + testing_path_suffix, nodisp=True, threads=1)


# Run Tests
start_time = time.time()

# Get list of architecture points
arch_list = [ get_path_to_arch() ]

# Get absolute metric for a list of architecture points
result_file = wotan_path + testing_path_suffix + '/wotan_final_4LUT_test_1.txt'


#vtr_tester.run()


# Finish
end_time = time.time()
print('Done. Took ' + str(round(end_time - start_time, 3)) + ' seconds')
