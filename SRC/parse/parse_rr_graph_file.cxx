
#include <iostream>
#include <fstream>
#include <cstring>
#include <cstdlib>
#include <cstdio>
#include <algorithm>
#include <unordered_map>
#include "exception.h"
#include "io.h"
#include "wotan_types.h"
#include "wotan_util.h"
#include "parse_rr_graph_file.h"

#include "pugixml.hpp"
#include "pugixml_util.hpp"

using namespace std;
using namespace pugiutil;

/*********************** Subroutines local to this module *******************/
void process_switches(Routing_Structs *routing_structs, pugi::xml_node parent, const pugiutil::loc_data &loc_data);

void process_grid(Arch_Structs *arch_structs, pugi::xml_node parent, const pugiutil::loc_data &loc_data);

void process_blocks(Arch_Structs *arch_structs, pugi::xml_node parent, const pugiutil::loc_data &loc_data);

void process_nodes(Routing_Structs *routing_structs, pugi::xml_node parent, const pugiutil::loc_data &loc_data);

void process_edges(Routing_Structs *routing_structs, pugi::xml_node parent, const pugiutil::loc_data &loc_data,
			int *wire_to_rr_ipin_switch, const int num_rr_switches);

void process_channels(t_chan_width &chan_width, int grid_width, int grid_height, pugi::xml_node parent, const pugiutil::loc_data &loc_data);

void process_rr_node_indices(Arch_Structs *arch_structs, Routing_Structs *routing_structs);

bool verify_rr_node_indices(Arch_Structs *arch_structs, const t_rr_node_indices &rr_node_indices, const t_rr_node &rr_nodes);

void get_grid_size(pugi::xml_node parent, const pugiutil::loc_data &loc_data, int &x_size, int &y_size);

void set_source_sink_coordinates (Arch_Structs *arch_structs, Routing_Structs *routing_structs);

/**** Function Definitions ****/
/* Parses the specified rr structs file according the specified rr structs mode */
void parse_rr_graph_file( std::string rr_graph_file, Arch_Structs *arch_structs, Routing_Structs *routing_structs, e_rr_graph_mode rr_graph_mode ) {

	cout << "Parsing xml file (" << rr_graph_file << ") in mode " << GRAPH_MODE_STRING[rr_graph_mode] << endl;

	pugi::xml_node next_component;

	pugi::xml_document doc;
	pugiutil::loc_data loc_data;

	if (check_file_extension(rr_graph_file, ".xml") == false) {
		WTHROW(EX_INIT, "RR graph file may be in incorrect format. Expecting .xml format" << endl);
	}

	try {
		loc_data = pugiutil::load_xml(doc, rr_graph_file);

		auto rr_graph = get_single_child(doc, "rr_graph", loc_data);

		if (rr_graph_mode == RR_GRAPH_SIMPLE) {
			/* Alloc rr nodes and count count nodes */
			int num_rr_nodes = count_children(next_component, "node", loc_data);
			routing_structs->alloc_and_create_rr_node(num_rr_nodes);
			cout << "Number of rr nodes: " << num_rr_nodes << endl;

			process_nodes(routing_structs, next_component, loc_data);

			/* Load switches */
			next_component = get_single_child(rr_graph, "switches", loc_data);

			int numSwitches = count_children(next_component, "switch", loc_data);
			routing_structs->alloc_and_create_rr_switch_inf(numSwitches);
			cout << "Number of rr switches: " << numSwitches << endl;

			process_switches(routing_structs, next_component, loc_data);

			/* Load edges */
			int wire_to_rr_ipin_switch = UNDEFINED;
			next_component = get_single_child(rr_graph, "rr_edges", loc_data);

			process_edges(routing_structs, next_component, loc_data, &wire_to_rr_ipin_switch, numSwitches);
		} else {
			int grid_height, grid_width;
			next_component = get_single_child(rr_graph, "grid", loc_data);
			get_grid_size(next_component, loc_data, grid_width, grid_height);

			t_chan_width nodes_per_chan;
			next_component = get_first_child(rr_graph, "channels", loc_data);
			process_channels(nodes_per_chan, grid_width, grid_height, next_component, loc_data);

			arch_structs->chan_width = nodes_per_chan;

			/* Decode the graph_type */
			//t_graph_type graph_type = GRAPH_BIDIR;

			//bool is_global_graph = (GRAPH_GLOBAL == graph_type ? true : false);
			bool is_global_graph = false;

			/* Global routing uses a single longwire track */
			int max_chan_width = (is_global_graph ? 1 : nodes_per_chan.max);
			cout << "Max channel width: " << max_chan_width << endl;

			/* Alloc rr nodes and count count nodes */
			next_component = get_single_child(rr_graph, "rr_nodes", loc_data);

			int num_rr_nodes = count_children(next_component, "node", loc_data);
			routing_structs->alloc_and_create_rr_node(num_rr_nodes);
			cout << "Number of rr nodes: " << num_rr_nodes << endl;

			process_nodes(routing_structs, next_component, loc_data);

			/* Load switches */
			next_component = get_single_child(rr_graph, "switches", loc_data);

			int numSwitches = count_children(next_component, "switch", loc_data);
			routing_structs->alloc_and_create_rr_switch_inf(numSwitches);
			cout << "Number of rr switches: " << numSwitches << endl;

			process_switches(routing_structs, next_component, loc_data);

			/* Load edges */
			int wire_to_rr_ipin_switch = UNDEFINED;
			next_component = get_single_child(rr_graph, "rr_edges", loc_data);

			process_edges(routing_structs, next_component, loc_data, &wire_to_rr_ipin_switch, numSwitches);

			/* Load block types */
			next_component = get_single_child(rr_graph, "block_types", loc_data);
			process_blocks(arch_structs, next_component, loc_data);

			/* Load grid */
			next_component = get_single_child(rr_graph, "grid", loc_data);
			process_grid(arch_structs, next_component, loc_data);
			arch_structs->set_block_types();

			/* Load rr node indicies */
			int x_size, y_size;
			arch_structs->get_grid_size(&x_size, &y_size);
			routing_structs->alloc_and_create_rr_node_index(NUM_RR_TYPES, NUM_SIDES, x_size, y_size);
			process_rr_node_indices(arch_structs, routing_structs);

			bool verified = verify_rr_node_indices(arch_structs, routing_structs->rr_node_indices, routing_structs->rr_node);
			if (verified == false)
				WTHROW(EX_INIT, rr_graph_file << ": Wrong rr_node_indices!");
			
			set_source_sink_coordinates (arch_structs, routing_structs);
		}
	} catch (XmlError &e) {
		WTHROW(EX_INIT, rr_graph_file << ":" << e.line() << ": " << e.what() << endl);
	}
}

/* Reads in the switch information and adds it to device_ctx.rr_switch_inf as specified*/
void process_switches(Routing_Structs *routing_structs, pugi::xml_node parent, const pugiutil::loc_data &loc_data) {
	pugi::xml_node Switch, SwitchSubnode;

	Switch = get_first_child(parent, "switch", loc_data);

	while (Switch) {
		int iSwitch = get_attribute(Switch, "id", loc_data).as_int();
		auto &rr_switch = routing_structs->rr_switch_inf[iSwitch];
		//const char* name = get_attribute(Switch, "name", loc_data, OPTIONAL).as_string(nullptr);

		std::string switch_type_str = get_attribute(Switch, "type", loc_data).as_string();
		//SwitchType switch_type = SwitchType::INVALID;
		//if (switch_type_str == "tristate") {
		//	switch_type = SwitchType::TRISTATE;
		//} else if (switch_type_str == "mux") {
		//	switch_type = SwitchType::MUX;
		//} else if (switch_type_str == "pass_gate") {
		//	switch_type = SwitchType::PASS_GATE;
		//} else if (switch_type_str == "short") {
		//	switch_type = SwitchType::SHORT;
		//} else if (switch_type_str == "buffer") {
		//	switch_type = SwitchType::BUFFER;
		//} else {
		//	VPR_THROW(VPR_ERROR_ROUTE, "Invalid switch type '%s'\n", switch_type_str.c_str());
		//}
		//rr_switch.set_type(switch_type);
		rr_switch.set_buffered(switch_type_str == "mux" || switch_type_str == "tristate"
								|| switch_type_str == "buffer");

		SwitchSubnode = get_single_child(Switch, "timing", loc_data, OPTIONAL);
		if (SwitchSubnode) {
			rr_switch.set_R(get_attribute(SwitchSubnode, "R", loc_data, OPTIONAL).as_float());
			rr_switch.set_Cin(get_attribute(SwitchSubnode, "Cin", loc_data, OPTIONAL).as_float());
			rr_switch.set_Cout(get_attribute(SwitchSubnode, "Cout", loc_data, OPTIONAL).as_float());
			rr_switch.set_Tdel(get_attribute(SwitchSubnode, "Tdel", loc_data, OPTIONAL).as_float());
		}
		SwitchSubnode = get_single_child(Switch, "sizing", loc_data);
		rr_switch.set_mux_trans_size(get_attribute(SwitchSubnode, "mux_trans_size", loc_data).as_float());
		rr_switch.set_buf_size(get_attribute(SwitchSubnode, "buf_size", loc_data).as_float());

		Switch = Switch.next_sibling(Switch.name());
	}
}

/* All channel info is read in and loaded into device_ctx.chan_width*/
void process_channels(t_chan_width &chan_width, int grid_width, int grid_height,
					  pugi::xml_node parent, const pugiutil::loc_data &loc_data) {
	pugi::xml_node channel, channelLists;

	channel = get_first_child(parent, "channel", loc_data);

	chan_width.max = get_attribute(channel, "chan_width_max", loc_data).as_uint();
	chan_width.x_min = get_attribute(channel, "x_min", loc_data).as_uint();
	chan_width.y_min = get_attribute(channel, "y_min", loc_data).as_uint();
	chan_width.x_max = get_attribute(channel, "x_max", loc_data).as_uint();
	chan_width.y_max = get_attribute(channel, "y_max", loc_data).as_uint();
	chan_width.x_list.resize(grid_height);
	chan_width.y_list.resize(grid_width);
        
	channelLists = get_first_child(parent, "x_list", loc_data);
	while (channelLists) {
		size_t index = get_attribute(channelLists, "index", loc_data).as_uint();
		int info = get_attribute(channelLists, "info", loc_data).as_float();

		if (index >= chan_width.x_list.size()) {
			WTHROW(EX_INIT, "Index " << index
				   << " on x list exceeds x_list size " << chan_width.x_list.size());
		}
		chan_width.x_list[index] = info;

		channelLists = channelLists.next_sibling(channelLists.name());
	}

	channelLists = get_first_child(parent, "y_list", loc_data);
	while (channelLists) {
		size_t index = get_attribute(channelLists, "index", loc_data).as_uint();
		int info = get_attribute(channelLists, "info", loc_data).as_float();

		if (index >= chan_width.y_list.size()) {
			WTHROW(EX_INIT, "Index " << index
				   << " on y list exceeds y_list size " << chan_width.y_list.size());
		}
		chan_width.y_list[index] = info;

		channelLists = channelLists.next_sibling(channelLists.name());
	}
}

/* Node info are processed. Seg_id of nodes are processed separately when rr_index_data is allocated*/
void process_nodes(Routing_Structs *routing_structs, pugi::xml_node parent, const pugiutil::loc_data &loc_data) {
	pugi::xml_node locSubnode, timingSubnode, segmentSubnode;
	pugi::xml_node rr_node;

	rr_node = get_first_child(parent, "node", loc_data);

	while (rr_node) {
		int inode = get_attribute(rr_node, "id", loc_data).as_int();
		auto &node = routing_structs->rr_node[inode];

		const char *node_type = get_attribute(rr_node, "type", loc_data).as_string();
		if (strcmp(node_type, "CHANX") == 0) {
			node.set_rr_type(CHANX);
		} else if (strcmp(node_type, "CHANY") == 0) {
			node.set_rr_type(CHANY);
		} else if (strcmp(node_type, "SOURCE") == 0) {
			node.set_rr_type(SOURCE);
		} else if (strcmp(node_type, "SINK") == 0) {
			node.set_rr_type(SINK);
		} else if (strcmp(node_type, "OPIN") == 0) {
			node.set_rr_type(OPIN);
		} else if (strcmp(node_type, "IPIN") == 0) {
			node.set_rr_type(IPIN);
		} else {
			WTHROW(EX_INIT, "" << __FILE__ << ":" << __LINE__
					<< "Valid inputs for class types are \"CHANX\", \"CHANY\",\"SOURCE\", \"SINK\",\"OPIN\", and \"IPIN\"."
					<< endl);
		}

		if (node.get_rr_type() == CHANX || node.get_rr_type() == CHANY) {
			const char *correct_direction = get_attribute(rr_node, "direction", loc_data).as_string();
			if (strcmp(correct_direction, "INC_DIR") == 0) {
				node.set_direction(INC_DIRECTION);
			} else if (strcmp(correct_direction, "DEC_DIR") == 0) {
				node.set_direction(DEC_DIRECTION);
			} else if (strcmp(correct_direction, "BI_DIR") == 0) {
				node.set_direction(BI_DIRECTION);
			} else {
				if (strcmp(correct_direction, "NO_DIR") != 0)
					WTHROW(EX_INIT, "Node's " << inode << " wrong direction: " << correct_direction << endl);
				node.set_direction(NO_DIRECTION);
			}
		}

		//node.set_capacity(get_attribute(rr_node, "capacity", loc_data).as_float());

		//--------------
		locSubnode = get_single_child(rr_node, "loc", loc_data);

		short x1, x2, y1, y2;
		x1 = get_attribute(locSubnode, "xlow", loc_data).as_float();
		x2 = get_attribute(locSubnode, "xhigh", loc_data).as_float();
		y1 = get_attribute(locSubnode, "ylow", loc_data).as_float();
		y2 = get_attribute(locSubnode, "yhigh", loc_data).as_float();

		if (node.get_rr_type() == IPIN || node.get_rr_type() == OPIN) {
			e_side side;
			std::string side_str = get_attribute(locSubnode, "side", loc_data).as_string();
			if (side_str == "LEFT") {
				side = LEFT;
			} else if (side_str == "RIGHT") {
				side = RIGHT;
			} else if (side_str == "TOP") {
				side = TOP;
			} else {
				if (side_str != "BOTTOM")
					WTHROW(EX_INIT, "Wrong node's " << inode << " location: " << side_str << endl);
				side = BOTTOM;
			}
			node.set_side(side);
		}

		node.set_coordinates(x1, y1, x2, y2);
		node.set_ptc_num(get_attribute(locSubnode, "ptc", loc_data).as_int());

		//-------
		timingSubnode = get_single_child(rr_node, "timing", loc_data, OPTIONAL);

		float R = 0.;
		float C = 0.;
		if (timingSubnode) {
			R = get_attribute(timingSubnode, "R", loc_data).as_float();
			C = get_attribute(timingSubnode, "C", loc_data).as_float();
		}
		node.set_R(R);
		node.set_C(C);

		//clear each node edge
		node.set_fan_in(0);

		//  <metadata>
		//	<meta name='grid_prefix' >CLBLL_L_</meta>
		//  </metadata>
		//auto metadata = get_single_child(rr_node, "metadata", loc_data, OPTIONAL);
		//if (metadata) {
		//	auto rr_node_meta = get_first_child(metadata, "meta", loc_data);
		//	while (rr_node_meta) {
		//		auto key = get_attribute(rr_node_meta, "name", loc_data).as_string();
		//
		//		vpr::add_rr_node_metadata(inode, key, rr_node_meta.child_value());
		//
		//		rr_node_meta = rr_node_meta.next_sibling(rr_node_meta.name());
		//	}
		//}

		rr_node = rr_node.next_sibling(rr_node.name());
	}
}

/*Loads the edges information from file into vpr. Nodes and switches must be loaded
 * before calling this function*/
void process_edges(Routing_Structs *routing_structs, pugi::xml_node parent, const pugiutil::loc_data &loc_data,
				int *wire_to_rr_ipin_switch, const int num_rr_switches) {
	pugi::xml_node edges;

	edges = get_first_child(parent, "edge", loc_data);
	//count the number of edges and store it in a vector
	vector<int> num_in_edges_for_node;
	vector<int> num_out_edges_for_node;
	num_in_edges_for_node.resize(routing_structs->rr_node.size(), 0);
	num_out_edges_for_node.resize(routing_structs->rr_node.size(), 0);

	while (edges) {
		size_t source_node = get_attribute(edges, "src_node", loc_data).as_uint();
		size_t sink_node = get_attribute(edges, "sink_node", loc_data).as_uint();
		if (source_node >= routing_structs->rr_node.size()) {
			WTHROW(EX_INIT, "" << __FILE__ << ":" << __LINE__ << "source_node " << source_node
					<< " is larger than rr_nodes.size() " << routing_structs->rr_node.size() << endl);
		}

		if (sink_node >= routing_structs->rr_node.size()) {
			WTHROW(EX_INIT,
				"" << __FILE__ << ":" << __LINE__ << "sink_node " << sink_node << " is larger than rr_nodes.size() "
				<< routing_structs->rr_node.size() << endl);
		}

		num_in_edges_for_node[sink_node]++;
		num_out_edges_for_node[source_node]++;
		edges = edges.next_sibling(edges.name());
	}


	//reset this vector in order to start count for num edges again
	for (size_t inode = 0; inode < routing_structs->rr_node.size(); inode++) {
		routing_structs->rr_node[inode].alloc_in_edges_and_switches(num_in_edges_for_node[inode]);
		routing_structs->rr_node[inode].alloc_out_edges_and_switches(num_out_edges_for_node[inode]);
		num_in_edges_for_node[inode] = 0;
		num_out_edges_for_node[inode] = 0;
	}

	edges = get_first_child(parent, "edge", loc_data);
	/* initialize a vector that keeps track of the number of wire to ipin switches
	 * There should be only one wire to ipin switch. In case there are more, make sure to
	 * store the most frequent switch */
	std::vector<int> count_for_wire_to_ipin_switches;
	count_for_wire_to_ipin_switches.resize(num_rr_switches, 0);
	//first is index, second is count
	pair<int, int> most_frequent_switch(-1, 0);

	while (edges) {
		size_t source_node = get_attribute(edges, "src_node", loc_data).as_uint();
		size_t sink_node = get_attribute(edges, "sink_node", loc_data).as_uint();
		int switch_id = get_attribute(edges, "switch_id", loc_data).as_int();

		if (switch_id >= num_rr_switches) {
			WTHROW(EX_INIT,
				"" << __FILE__ << ":" << __LINE__ << "switch_id " << switch_id << " is larger than num_rr_switches "
				<< num_rr_switches << endl);
		}

		/*Keeps track of the number of the specific type of switch that connects a wire to an ipin
		 * use the pair data structure to keep the maximum*/
		if (routing_structs->rr_node[source_node].get_rr_type() == CHANX ||
			routing_structs->rr_node[source_node].get_rr_type() == CHANY) {
			if (routing_structs->rr_node[sink_node].get_rr_type() == IPIN) {
				count_for_wire_to_ipin_switches[switch_id]++;
				if (count_for_wire_to_ipin_switches[switch_id] > most_frequent_switch.second) {
					most_frequent_switch.first = switch_id;
					most_frequent_switch.second = count_for_wire_to_ipin_switches[switch_id];
				}
			}
		}
		//set edge in correct rr_node data structure
		routing_structs->rr_node[source_node].out_edges[num_out_edges_for_node[source_node]] = sink_node;
		routing_structs->rr_node[source_node].out_switches[num_out_edges_for_node[source_node]] = switch_id;

		routing_structs->rr_node[sink_node].in_edges[num_in_edges_for_node[sink_node]] = source_node;
		routing_structs->rr_node[sink_node].in_switches[num_in_edges_for_node[sink_node]] = switch_id;

		// Read the metadata for the edge
		//auto metadata = get_single_child(edges, "metadata", loc_data, OPTIONAL);
		//if (metadata) {
		//	auto edges_meta = get_first_child(metadata, "meta", loc_data);
		//	while (edges_meta) {
		//		auto key = get_attribute(edges_meta, "name", loc_data).as_string();
		//
		//		vpr::add_rr_edge_metadata(source_node, sink_node, switch_id,
		//								  key, edges_meta.child_value());
		//
		//		edges_meta = edges_meta.next_sibling(edges_meta.name());
		//	}
		//}
		num_in_edges_for_node[sink_node]++;
		num_out_edges_for_node[source_node]++;

		edges = edges.next_sibling(edges.name()); //Next edge
	}
	*wire_to_rr_ipin_switch = most_frequent_switch.first;
	num_in_edges_for_node.clear();
	num_out_edges_for_node.clear();

	count_for_wire_to_ipin_switches.clear();
}

/* count number ob block pins */
static void init_block_pins(pugi::xml_node pin_class, const pugiutil::loc_data &loc_data,
							int num_class, Physical_Type_Descriptor& ptd) {

	int num_pins = 0;
	int num_drivers = 0;
	int num_receivers = 0;

	for (int classNum = 0; classNum < num_class; classNum++) {
		const char *typeInfo = get_attribute(pin_class, "type", loc_data).value();
		e_pin_type type;

		if (strcmp(typeInfo, "OUTPUT") == 0) {
			type = DRIVER;
		} else if (strcmp(typeInfo, "INPUT") == 0) {
			type = RECEIVER;
		} else {
			type = OPEN;
		}

		int loc_pins = 0;
		pugi::xml_node pin = get_first_child(pin_class, "pin", loc_data, REQUIRED);

		while (pin) {
			bool is_global = get_attribute(pin, "is_global", loc_data, OPTIONAL).as_bool();
			if (is_global == false)	++loc_pins;
			pin = pin.next_sibling();
		}

		if (type == DRIVER)
			num_drivers += loc_pins;
		else if (type == RECEIVER)
			num_receivers += loc_pins;

		num_pins += count_children(pin_class, loc_data, REQUIRED);
		pin_class = pin_class.next_sibling();
	}

	ptd.set_num_pins(num_pins);
	ptd.set_num_drivers(num_drivers);
	ptd.set_num_receivers(num_receivers);

	ptd.pin_class.assign(num_pins, UNDEFINED);
	ptd.is_global_pin.assign(num_pins, false);
}

/* Initialize blocks from the RR graph file. */
void process_blocks(Arch_Structs *arch_structs, pugi::xml_node parent, const pugiutil::loc_data &loc_data) {
	pugi::xml_node Block;
	pugi::xml_node pin_class;
	pugi::xml_node pin;

	Block = get_first_child(parent, "block_type", loc_data);
	int num_blocks = count_children(parent, "block_type", loc_data, OPTIONAL);
	arch_structs->alloc_and_create_block_type(num_blocks);

	while (Block) {
		int id = get_attribute(Block, "id", loc_data).as_int(0);
		Physical_Type_Descriptor &ptd = arch_structs->block_type[id];
		ptd.set_index(id);

		const char *name = get_attribute(Block, "name", loc_data).as_string(nullptr);
		ptd.set_name(string(name));

		int width = get_attribute(Block, "width", loc_data).as_float(0);
		ptd.set_width(width);
		int height = get_attribute(Block, "height", loc_data).as_float(0);
		ptd.set_height(height);

		pin_class = get_first_child(Block, "pin_class", loc_data, OPTIONAL);
		int num_class = count_children(Block, "pin_class", loc_data, OPTIONAL);

		init_block_pins(pin_class, loc_data, num_class, ptd);

		pin_class = get_first_child(Block, "pin_class", loc_data, OPTIONAL);

		for (int classNum = 0; classNum < num_class; classNum++) {
			Pin_Class class_inf;

			/*Verify types and pins*/
			const char *typeInfo = get_attribute(pin_class, "type", loc_data).value();
			if (strcmp(typeInfo, "OPEN") == 0) {
				class_inf.set_pin_type(OPEN);
			} else if (strcmp(typeInfo, "OUTPUT") == 0) {
				class_inf.set_pin_type(DRIVER);
			} else if (strcmp(typeInfo, "INPUT") == 0) {
				class_inf.set_pin_type(RECEIVER);
			} else {
				WTHROW(EX_INIT, "" << __FILE__ << ":" << __LINE__
						<< "Valid inputs for class types are \"OPEN\", \"OUTPUT\", and \"INPUT\"." << endl);
				class_inf.set_pin_type(OPEN);
			}

			long num_pins = (long) count_children(pin_class, "pin", loc_data);
			class_inf.pinlist.reserve(num_pins);

			pin = get_first_child(pin_class, "pin", loc_data, OPTIONAL);

			while (pin) {
				auto num = get_attribute(pin, "ptc", loc_data).as_uint();
				class_inf.pinlist.push_back(num);
				ptd.pin_class[num] = classNum;

				bool is_global = get_attribute(pin, "is_global", loc_data, OPTIONAL).as_bool();
				if (is_global == true) {
					ptd.is_global_pin[num] = is_global;
				}

				pin = pin.next_sibling();
			}

			ptd.class_inf.push_back(class_inf);

			pin_class = pin_class.next_sibling();
		}

		Block = Block.next_sibling(Block.name());
	}
}

/* Initialize grid from the routing graph file */
void process_grid(Arch_Structs *arch_structs, pugi::xml_node parent, const pugiutil::loc_data &loc_data) {
	pugi::xml_node grid_node;
	int num_grid_node = count_children(parent, "grid_loc", loc_data);

	int x_size, y_size;
	get_grid_size(parent, loc_data, x_size, y_size);
	arch_structs->alloc_and_create_grid(x_size, y_size);

	grid_node = get_first_child(parent, "grid_loc", loc_data);
	for (int i = 0; i < num_grid_node; i++) {
		int x = get_attribute(grid_node, "x", loc_data).as_float();
		int y = get_attribute(grid_node, "y", loc_data).as_float();

		int block_type_id = get_attribute(grid_node, "block_type_id", loc_data).as_int(0);
		arch_structs->grid.at(x).at(y).set_type_index(block_type_id);

		int width = get_attribute(grid_node, "width_offset", loc_data).as_int(0);
		arch_structs->grid.at(x).at(y).set_width_offset(width);
		int height = get_attribute(grid_node, "height_offset", loc_data).as_int(0);
		arch_structs->grid.at(x).at(y).set_height_offset(height);

		grid_node = grid_node.next_sibling(grid_node.name());
	}
}

/*Allocates and load the rr_node look up table. SINK and SOURCE, IPIN and OPIN
 *share the same look up table. CHANX and CHANY have individual look ups */
void process_rr_node_indices(Arch_Structs *arch_structs, Routing_Structs *routing_structs) {
	/* Alloc the lookup table */
	auto &indices = routing_structs->rr_node_indices;

	typedef struct max_ptc {
		short chanx_max_ptc = 0;
		short chany_max_ptc = 0;
	} t_max_ptc;

	const int grid_height = arch_structs->get_grid_height();
	const int grid_width  = arch_structs->get_grid_width();

	/*
	 * Local multi-dimensional vector to hold max_ptc for every coordinate.
	 * It has same height and width as CHANY and CHANX are inverted
	 */
	vector<vector<t_max_ptc> > coordinates_max_ptc; /* [x][y] */
	size_t max_coord_size = std::max(grid_height, grid_width);
	coordinates_max_ptc.resize(max_coord_size, vector<t_max_ptc>(max_coord_size));

	/* Alloc the lookup table */
	for (e_rr_type rr_type : RR_TYPES) {
		if (rr_type == CHANX) {
			indices[rr_type].resize(grid_height);
			for (int y = 0; y < grid_height; ++y) {
				indices[rr_type][y].resize(grid_width);
				for (int x = 0; x < grid_width; ++x) {
					indices[rr_type][y][x].resize(NUM_SIDES);
				}
			}
		} else {
			indices[rr_type].resize(grid_width);
			for (int x = 0; x < grid_width; ++x) {
				indices[rr_type][x].resize(grid_height);
				for (int y = 0; y < grid_height; ++y) {
					indices[rr_type][x][y].resize(NUM_SIDES);
				}
			}
		}
	}

	/*
	 * Add the correct node into the vector
	 * For CHANX and CHANY no node is added yet, but the maximum ptc is counted for each
	 * x/y location. This is needed later to add the correct node corresponding to CHANX
	 * and CHANY.
	 *
	 * Note that CHANX and CHANY 's x and y are swapped due to the chan and seg convention.
	 */
	for (int inode = 0; inode < routing_structs->get_num_rr_nodes(); inode++) {
		auto &node = routing_structs->rr_node[inode];
		const auto rr_type = node.get_rr_type();
		const short ptc_num = node.get_ptc_num();

		if (rr_type == SOURCE || rr_type == SINK) {
			for (int ix = node.get_xlow(); ix <= node.get_xhigh(); ix++) {
				for (int iy = node.get_ylow(); iy <= node.get_yhigh(); iy++) {
					if (ptc_num >= (int)indices[SOURCE][ix][iy][0].size()) {
						indices[SOURCE][ix][iy][0].resize(ptc_num + 1, OPEN);
					}
					if (ptc_num >= (int)indices[SINK][ix][iy][0].size()) {
						indices[SINK][ix][iy][0].resize(ptc_num + 1, OPEN);
					}
					indices[rr_type][ix][iy][0][ptc_num] = inode;
				}
			}
		} else if (rr_type == IPIN || rr_type == OPIN) {
			const e_side side = node.get_side();

			for (int ix = node.get_xlow(); ix <= node.get_xhigh(); ix++) {
				for (int iy = node.get_ylow(); iy <= node.get_yhigh(); iy++) {
					if (ptc_num >= (int)indices[OPIN][ix][iy][side].size()) {
						indices[OPIN][ix][iy][side].resize(ptc_num + 1, OPEN);
					}
					if (ptc_num >= (int)indices[IPIN][ix][iy][side].size()) {
						indices[IPIN][ix][iy][side].resize(ptc_num + 1, OPEN);
					}
					indices[rr_type][ix][iy][side][ptc_num] = inode;
				}
			}
		} else if (rr_type == CHANX) {
			for (int ix = node.get_xlow(); ix <= node.get_xhigh(); ix++) {
				for (int iy = node.get_ylow(); iy <= node.get_yhigh(); iy++) {
					coordinates_max_ptc[iy][ix].chanx_max_ptc = std::max(coordinates_max_ptc[iy][ix].chanx_max_ptc, ptc_num);
				}
			}
		} else if (rr_type == CHANY) {
			for (int ix = node.get_xlow(); ix <= node.get_xhigh(); ix++) {
				for (int iy = node.get_ylow(); iy <= node.get_yhigh(); iy++) {
					coordinates_max_ptc[ix][iy].chany_max_ptc = std::max(coordinates_max_ptc[ix][iy].chany_max_ptc, ptc_num);
				}
			}
		}
	}

	/* Alloc the lookup table */
	for (e_rr_type rr_type : RR_TYPES) {
		if (rr_type == CHANX) {
			for (int y = 0; y < grid_height; ++y) {
				for (int x = 0; x < grid_width; ++x) {
					indices[CHANX][y][x][0].resize(coordinates_max_ptc[y][x].chanx_max_ptc + 1, OPEN);
				}
			}
		} else if (rr_type == CHANY) {
			for (int x = 0; x < grid_width; ++x) {
				for (int y = 0; y < grid_height; ++y) {
					indices[CHANY][x][y][0].resize(coordinates_max_ptc[x][y].chany_max_ptc + 1, OPEN);
				}
			}
		}
	}

	int ptc_num;
	/* CHANX and CHANY need to reevaluated with its ptc num as the correct index*/
	for (int inode = 0; inode < routing_structs->get_num_rr_nodes(); inode++) {
		auto &node = routing_structs->rr_node[inode];
		if (node.get_rr_type() == CHANX) {
			for (int iy = node.get_ylow(); iy <= node.get_yhigh(); iy++) {
				for (int ix = node.get_xlow(); ix <= node.get_xhigh(); ix++) {
					ptc_num = node.get_ptc_num();
					if (ptc_num >= int(indices[CHANX][iy][ix][0].size())) {
						WTHROW(EX_INIT, "Ptc index" << ptc_num << " for CHANX (" << ix << ", " << iy
								<< ") is out of bounds, size = " << indices[CHANX][iy][ix][0].size()
								<< endl);
					}
					indices[CHANX][iy][ix][0][ptc_num] = inode;
				}
			}
		} else if (node.get_rr_type() == CHANY) {
			for (int ix = node.get_xlow(); ix <= node.get_xhigh(); ix++) {
				for (int iy = node.get_ylow(); iy <= node.get_yhigh(); iy++) {
					ptc_num = node.get_ptc_num();
					if (ptc_num >= int(indices[CHANY][ix][iy][0].size())) {
						WTHROW(EX_INIT, "Ptc index" << ptc_num << " for CHANY (" << ix << ", " << iy
								<< ") is out of bounds, size = " << indices[CHANY][ix][iy][0].size()
								<< endl);
					}
					indices[CHANY][ix][iy][0][ptc_num] = inode;
				}
			}
		}
	}

	// Copy the SOURCE/SINK nodes to all offset positions for blocks with width > 1 and/or height > 1
	// This ensures that look-ups on non-root locations will still find the correct SOURCE/SINK
	for (int x = 0; x < grid_width; x++) {
		for (int y = 0; y < grid_height; y++) {
			int width_offset = arch_structs->grid[x][y].get_width_offset();
			int height_offset = arch_structs->grid[x][y].get_height_offset();
			if (width_offset != 0 || height_offset != 0) {
				int root_x = x - width_offset;
				int root_y = y - height_offset;
	
				indices[SOURCE][x][y][0] = indices[SOURCE][root_x][root_y][0];
				indices[SINK][x][y][0] = indices[SINK][root_x][root_y][0];
			}
		}
	}

	routing_structs->rr_node_indices = indices;
}

static std::string describe_rr_node(const t_rr_node &rr_nodes, int inode) {
	std::ostringstream msgStream;
	msgStream << "RR node: " << inode;

	auto rr_node = rr_nodes[inode];

	msgStream << " type: " << rr_node.get_rr_type_string();

	msgStream << " location: (" << rr_node.get_xlow() << ", " << rr_node.get_ylow() << ")";

	if (rr_node.get_xlow() != rr_node.get_xhigh() || rr_node.get_ylow() != rr_node.get_yhigh()) {
		msgStream << " <-> (" << rr_node.get_xhigh() << ", " << rr_node.get_yhigh() << ")";
	}

	if (rr_node.get_rr_type() == CHANX || rr_node.get_rr_type() == CHANY) {
		msgStream << " channel: " << rr_node.get_ptc_num();
	} else if (rr_node.get_rr_type() == IPIN || rr_node.get_rr_type() == OPIN) {
		msgStream << " pin: " << rr_node.get_ptc_num() << " side: " << rr_node.side_string();
	} else {
		if (!(rr_node.get_rr_type() == SOURCE || rr_node.get_rr_type() == SINK))
                    WTHROW(EX_INIT, "ASSERT");

		msgStream << " class: " << rr_node.get_ptc_num();
	}

	std::string msg = msgStream.str();
	return msg;
}

bool verify_rr_node_indices(Arch_Structs *arch_structs, const t_rr_node_indices& rr_node_indices, const t_rr_node& rr_nodes) {
	std::unordered_map<int, int> rr_node_counts;

	for (e_rr_type rr_type : RR_TYPES) {
		int width = arch_structs->get_grid_width();
		int height = arch_structs->get_grid_height();

		//CHANX bizarely stores with x/y swapped...
		if (rr_type == CHANX) {
			std::swap(width, height);
		}

		for (int x = 0; x < width; ++x) {
			for (int y = 0; y < height; ++y) {
				for (e_side side : SIDES) {
					for (int inode : rr_node_indices[rr_type][x][y][side]) {
						if (inode < 0) continue;

						rr_node_counts[inode]++;

						auto& rr_node = rr_nodes[inode];

						if (rr_node.get_rr_type() != rr_type) {
							WTHROW(EX_INIT, "RR node type does not match between rr_nodes and rr_node_indices (" << rr_node_typename[rr_node.get_rr_type()]
									<< "/" << rr_node_typename[rr_type] << "): " << describe_rr_node(rr_nodes, inode).c_str());
						}

						if (rr_node.get_rr_type() == CHANX) {
							//CHANX has this bizare swapped x / y storage...
							std::swap(x, y);

							if (rr_node.get_ylow() != rr_node.get_yhigh())
								WTHROW(EX_INIT, "CHANX should be horizontal");

							if (y != rr_node.get_ylow()) {
								WTHROW(EX_INIT, "RR node y position does not agree between rr_nodes (" << rr_node.get_ylow()
									   << ") and rr_node_indices (" << y << "): " << describe_rr_node(rr_nodes, inode).c_str());
							}

							if (x < rr_node.get_xlow() || x > rr_node.get_xhigh()) {
								WTHROW(EX_INIT, "RR node x positions do not agree between rr_nodes (" << rr_node.get_xlow()
									   << " <-> " << rr_node.get_xhigh() << ") and rr_node_indices (" << x << "): " <<
										  describe_rr_node(rr_nodes, inode).c_str());
							}

							std::swap(x, y); //Swap back
						} else if (rr_node.get_rr_type() == CHANY) {
							if (rr_node.get_xlow() != rr_node.get_xhigh())
								WTHROW(EX_INIT, "CHANY should be veritcal");

							if (x != rr_node.get_xlow()) {
								WTHROW(EX_INIT, "RR node x position does not agree between rr_nodes (" << rr_node.get_xlow() <<
									   ") and rr_node_indices (" << x << "): " << describe_rr_node(rr_nodes, inode).c_str());
							}

							if (y < rr_node.get_ylow() || y > rr_node.get_yhigh()) {
								WTHROW(EX_INIT, "RR node y positions do not agree between rr_nodes ("
									   << rr_node.get_ylow() << " <-> " << rr_node.get_yhigh() << ") and rr_node_indices ("
									   << y << "): " << describe_rr_node(rr_nodes, inode).c_str());
							}
						} else if (rr_node.get_rr_type() == SOURCE || rr_node.get_rr_type() == SINK) {
							//Sources have co-ordintes covering the entire block they are in
							if (x < rr_node.get_xlow() || x > rr_node.get_xhigh()) {
								WTHROW(EX_INIT, "RR node x positions do not agree between rr_nodes (" << rr_node.get_xlow()
									   << " <-> " << rr_node.get_xhigh() << ") and rr_node_indices (" << x << "): " <<
										  describe_rr_node(rr_nodes, inode).c_str());
							}

							if (y < rr_node.get_ylow() || y > rr_node.get_yhigh()) {
								WTHROW(EX_INIT, "RR node y positions do not agree between rr_nodes ("
									   << rr_node.get_ylow() << " <-> " << rr_node.get_yhigh() << ") and rr_node_indices ("
									   << y << "): " << describe_rr_node(rr_nodes, inode).c_str());
							}

						} else {
							if (!(rr_node.get_rr_type() == IPIN || rr_node.get_rr_type() == OPIN))
                                                            WTHROW(EX_INIT, "ASSERT");
							/* As we allow a pin to be indexable on multiple sides,
							 * This check code should be invalid
								if (rr_node.get_xlow() != x) {
									WTHROW(EX_INIT, "RR node xlow does not match between rr_nodes and rr_node_indices (" << rr_node.get_xlow() <<
										   "/" << x << "): " << describe_rr_node(rr_nodes, inode).c_str());
								}

								if (rr_node.get_ylow() != y) {
									WTHROW(EX_INIT, "RR node ylow does not match between rr_nodes and rr_node_indices (" << rr_node.get_ylow() <<
										   "/)" << y << ": " << describe_rr_node(rr_nodes, inode).c_str());
								}
							*/
						}

						if (rr_type == IPIN || rr_type == OPIN) {
							/* As we allow a pin to be indexable on multiple sides,
							 * This check code should be invalid
								if (rr_node.get_side() != side) {
									WTHROW(EX_INIT, "RR node xlow does not match between rr_nodes and rr_node_indices (" << SIDE_STRING[rr_node.get_side()] <<
										   "/" << SIDE_STRING[side] << "): " << describe_rr_node(rr_nodes, inode).c_str());
								} else {
									assert(rr_node.get_side() == side);
								}
							*/
						} else { //Non-pin's don't have sides, and should only be in side 0
							if (side != SIDES[0]) {
								WTHROW(EX_INIT, "Non-Pin RR node in rr_node_indices found with non-default side" <<
										  SIDE_STRING[side] << ": " << describe_rr_node(rr_nodes, inode).c_str());
							} else {
								if (side != 0)
                                                                    WTHROW(EX_INIT, "ASSERT");
							}
						}
					}
				}
			}
		}
	}

	if (rr_node_counts.size() != rr_nodes.size()) {
		WTHROW(EX_INIT, "Mismatch in number of unique RR nodes in rr_nodes (" << rr_nodes.size() << ") and rr_node_indices (" << rr_node_counts.size() << ")");
	}

	for (auto kv : rr_node_counts) {
		int inode = kv.first;
		int count = kv.second;

		auto& rr_node = rr_nodes[inode];

		if (rr_node.get_rr_type() == SOURCE || rr_node.get_rr_type() == SINK) {
			int rr_width = (rr_node.get_xhigh() - rr_node.get_xlow() + 1);
			int rr_height = (rr_node.get_yhigh() - rr_node.get_ylow() + 1);
			int rr_area = rr_width * rr_height;
			if (count != rr_area) {
				WTHROW(EX_INIT, "Mismatch between RR node size (" << rr_area << ") and count within rr_node_indices ("
					   << count << "): " << describe_rr_node(rr_nodes, inode).c_str());
			}
		} else {
			int length = std::max(rr_node.get_xhigh() - rr_node.get_xlow(), rr_node.get_yhigh() - rr_node.get_ylow());
			if (count != length + 1) {
				WTHROW(EX_INIT, "Mismatch between RR node length (" << length << ") and count within rr_node_indices ("
					   << count << "), should be length + 1): " << describe_rr_node(rr_nodes, inode).c_str());
			}
		}
	}

	return true;
}

/* Set xs, ys for all SOURCE, SINK */
void set_source_sink_coordinates (Arch_Structs *arch_structs, Routing_Structs *routing_structs) {
	for (e_rr_type rr_type : RR_TYPES) {
		int width = arch_structs->get_grid_width();
		int height = arch_structs->get_grid_height();

		if (rr_type != SOURCE && rr_type != SINK) {
			continue;
		}
		
		for (int x = 0; x < width; ++x) {
			for (int y = 0; y < height; ++y) {
				for (e_side side : SIDES) {
					for (int inode : routing_structs->rr_node_indices[rr_type][x][y][side]) {
						if (inode < 0) continue;

						auto& rr_node = routing_structs->rr_node[inode];

						if (rr_node.get_rr_type() != rr_type) {
							WTHROW(EX_INIT, "RR node type does not match between rr_nodes and rr_node_indices (" << rr_node_typename[rr_node.get_rr_type()]
									<< "/" << rr_node_typename[rr_type] << "): " << describe_rr_node(routing_structs->rr_node, inode).c_str());
						}
						
						int *edges, num_edges;
						if (rr_type == SOURCE) {
							edges = rr_node.out_edges;
							num_edges = rr_node.get_num_out_edges();
						} else {
							edges = rr_node.in_edges;
							num_edges = rr_node.get_num_in_edges();
						}
						
						
						int xs = UNDEFINED, ys = UNDEFINED;
						for (int iedge = 0; iedge < num_edges; iedge++) {
							auto& to_node = routing_structs->rr_node[edges[iedge]];
							
							int xlow = to_node.get_xlow();
							int ylow = to_node.get_ylow();
							
							if (xs == UNDEFINED && ys == UNDEFINED) {
								xs = xlow;
								ys = ylow;
							} else {
								if (xs != xlow && ys != ylow) {
									WTHROW(EX_INIT, "RR node " << rr_node_typename[rr_type] << "(" << inode << ") is connected to pins located at different locations:" << endl
										<< "Some nodes are located at (" << xs << ", " << ys << ") and some (" << edges[iedge] << ") at (" << xlow << ", " << ylow << ")");
								}
							}
						} 
						
						rr_node.set_source_sink_coordinates(xs, ys);
					}
				}
			}
		}
	}
		
}

/* If Wotan is being initialized based on an rr structs file then backwards edges/switches need to be determined
   for each node as a post-processing step. Do this for the pins specified by 'node_type'. if node_type == UNDEFINED,
   then do this for all nodes  */
void initialize_reverse_node_edges_and_switches(Routing_Structs *routing_structs, int node_type) {
	/* setting the incoming edges/switches for each node can be done in two passes over the graph. once to determine the list of switches/edges
	   for each node, and once to set this information for each node */

	int num_nodes = routing_structs->get_num_rr_nodes();

	/* vector of vectors to hold incoming edges and switches for each node */
	vector<vector<int> > inc_switches, inc_edges;
	inc_switches.assign(num_nodes, vector<int>());
	inc_edges.assign(num_nodes, vector<int>());

	/* pass 1 - determine what the incoming edges/switches are for each node */
	for (int inode = 0; inode < num_nodes; inode++) {
		int from_node_ind = inode;
		RR_Node &rr_node = routing_structs->rr_node[from_node_ind];

		/* for each destination node mark which node the connection is coming from and which switch it uses */
		for (int i_out_edge = 0; i_out_edge < rr_node.get_num_out_edges(); i_out_edge++) {
			int to_node_ind = rr_node.out_edges[i_out_edge];
			int switch_ind = rr_node.out_switches[i_out_edge];

			inc_switches[to_node_ind].push_back(switch_ind);
			inc_edges[to_node_ind].push_back(from_node_ind);
		}
	}

	/* pass 2 - allocate and set incoming switch/edge structures for each node */
	for (int inode = 0; inode < num_nodes; inode++) {
		RR_Node *rr_node = &routing_structs->rr_node[inode];

		if (node_type != UNDEFINED) {
			/* skip nodes that aren't of 'node_type' */
			if (rr_node->get_rr_type() != (e_rr_type) node_type) {
				continue;
			}
		}

		int num_inc_edges = (int) inc_edges[inode].size();

		rr_node->free_in_edges_and_switches();

		if (num_inc_edges > 0 && rr_node->get_num_in_edges() == UNDEFINED) {
			/* allocate the incoming switches/edges for this node */
			rr_node->alloc_in_edges_and_switches(num_inc_edges);

			/* set incoming switches/edges */
			for (int iedge = 0; iedge < num_inc_edges; iedge++) {
				rr_node->in_edges[iedge] = inc_edges[inode][iedge];
				rr_node->in_switches[iedge] = inc_switches[inode][iedge];
			}
		}
	}
}

/*  */
void get_grid_size(pugi::xml_node parent, const pugiutil::loc_data &loc_data, int &x_size, int &y_size) {
	pugi::xml_node grid_node;

	int num_grid_node = count_children(parent, "grid_loc", loc_data);
	grid_node = get_first_child(parent, "grid_loc", loc_data);

	int xmax = UNDEFINED, ymax = UNDEFINED;

	for (int i = 0; i < num_grid_node; i++) {
		int x = get_attribute(grid_node, "x", loc_data).as_float();
		int y = get_attribute(grid_node, "y", loc_data).as_float();

		if (xmax == UNDEFINED || xmax < x)
			xmax = x;
		if (ymax == UNDEFINED || ymax < y)
			ymax = y;
		grid_node = grid_node.next_sibling(grid_node.name());
	}

	x_size = xmax + 1;
	y_size = ymax + 1;
}
