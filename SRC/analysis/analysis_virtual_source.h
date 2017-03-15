#ifndef ANALYSIS_VIRTUAL_SOURCE_H
#define ANALYSIS_VIRTUAL_SOURCE_H

#include <vector>
#include "wotan_types.h"

using namespace std;

/**** Function Declarations ****/
void print_ss_dist(t_ss_distances &ss_distances);
int get_sink_node_ind(Routing_Structs *routing_structs, int current_sink_ind);
void propagate_backwards(int from_node_ind, t_rr_node &rr_node, t_node_topo_inf &node_topo_inf,
						 vector<int> &virtual_sources, float prob_reachable, User_Options *user_opts,
						 t_ss_distances &ss_distances, int max_path_weight, int level, vector<bool> &visited);
float get_prob_reachable(double *source_buckets, int num_source_buckets);

#endif
