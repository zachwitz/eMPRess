# ReconBuilder.py
# This code builds a representation of a host tree, parasite tree, and a reconfiguration
# as specified in Recon.py using the host tree, parasite tree, and reconfiguration 
# representation in the DTL.

from empress.topo_sort.Tree import NodeLayout
from empress.topo_sort.Tree import TreeType
from empress.topo_sort.tree_format_converter import dict_to_tree

__all__ = ["build_trees_with_temporal_order"]

def build_trees_with_temporal_order(host_tree, parasite_tree, reconciliation):
    """
    This function uses topological sort to order the nodes inside host and parasite tree.
    The output trees can be used for visualization.
    
    :param host_tree: host tree dictionary
    :param parasite_tree: parasite tree dictionary
    :param reconciliation: reconciliation dictionary
    :return: a Tree object of type HOST, a Tree object of type PARASITE, and a boolean
             indicator of whether the reconciliation is temporally consistent. If the
             reconciliation is temporally consistent, then the tree objects have their
             nodes populated and the nodes will contain the temporal order information
             in the layout field. If the reconciliation is temporally inconsistent, the
             function returns None, None, False.
    """
    # find the temporal order for host nodes and parasite nodes
    temporal_graph = build_temporal_graph(host_tree, parasite_tree, reconciliation)
    ordering_dict = topological_order(temporal_graph)

    host_tree_object = dict_to_tree(host_tree, TreeType.HOST)
    parasite_tree_object = dict_to_tree(parasite_tree, TreeType.PARASITE)

    # if there is a valid temporal ordering, we populate the layout with the order corresponding to the node
    if ordering_dict != None:
        # calculate the temporal order for leaves, which all have the largest order
        max_order = 1
        for node in ordering_dict:
            if max_order < ordering_dict[node]:
                max_order = ordering_dict[node]
        leaf_order = max_order + 1
        populate_nodes_with_order(host_tree_object.root_node, TreeType.HOST, ordering_dict, leaf_order)
        populate_nodes_with_order(parasite_tree_object.root_node, TreeType.PARASITE, ordering_dict, leaf_order)
        return host_tree_object, parasite_tree_object, True
    else:
        return None, None, False

def create_parent_dict(host_tree, parasite_tree):
    """
    :param host_tree:  host tree dictionary
    :param parasite_tree:  parasite tree dictionary
    :return: A dictionary that maps the name of a child node to the name of its parent
             for both the host tree and the parasite tree.
    """
    parent_dict = {}
    for edge_name in host_tree:
        child_node = _bottom_node(host_tree[edge_name])
        parent_node = _top_node(host_tree[edge_name])
        parent_dict[child_node] = parent_node
    for edge_name in parasite_tree:
        child_node = _bottom_node(parasite_tree[edge_name])
        parent_node = _top_node(parasite_tree[edge_name])
        parent_dict[child_node] = parent_node
    return parent_dict

def build_formatted_tree(tree):
    """
    :param tree:  a tree dictionary
    :return: A temporal graph that contains all the temporal relations implied by
             the tree. Each key is a node tuple of the form (name, type) where name
             is a string representing the name of a parasite or host tree INTERNAL 
             node and type is either TreeType.HOST or TreeType.PARASITE which are 
             defined in Recon.py. The associated value is a list of node tuples that
             are the children of this node tuple in the tree.
    """
    tree_type = None
    if 'pTop' in tree:
        tree_type = TreeType.PARASITE
    else:
        tree_type = TreeType.HOST

    formatted_tree = {}
    for edge_name in tree:
        edge_four_tuple = tree[edge_name]
        # the temporal graph does not contain leaves as keys
        if _is_leaf_edge(edge_four_tuple):
            continue
        # the temporal graph contains internal node tuples as keys,
        # and their children nodes tuples as values
        node_name = _bottom_node(edge_four_tuple)
        left_child_name = edge_four_tuple[2][1]
        right_child_name = edge_four_tuple[3][1]
        formatted_tree[(node_name, tree_type)] = [(left_child_name, tree_type), \
                                               (right_child_name, tree_type)]
    return formatted_tree

def uniquify(elements):
    """
    :param elements:  a list whose elements might not be unique
    :return: A list that contains only the unique elements of the input list. 
    """
    return list(set(elements))

def build_temporal_graph(host_tree, parasite_tree, reconciliation):
    """
    :param host_tree:  host tree dictionary
    :param parasite_tree:  parasite tree dictionary
    :param reconciliation:  reconciliation dictionary
    :return: The temporal graph which is defined as follows:
        Each key is a node tuple of the form (name, type) where name is a string representing
        the name of a parasite or host tree INTERNAL node and type is either TreeType.HOST or 
        TreeType.PARASITE which are defined in Recon.py. 
        Note that leaves of the host and parasite trees are not considered here.
        The associated value is a list of node tuples that are the children of this node tuple
        in the temporal graph.
    """
    # create a dictionary that maps each host and parasite node to its parent
    parent = create_parent_dict(host_tree, parasite_tree)
    # create temporal graphs for the host and parasite tree
    temporal_host_tree = build_formatted_tree(host_tree)
    temporal_parasite_tree = build_formatted_tree(parasite_tree)
    # initialize the final temporal graph to the combined temporal graphs of host and parasite tree
    temporal_graph = temporal_host_tree
    temporal_graph.update(temporal_parasite_tree)
    # add temporal relations implied by each node mapping and the corresponding event
    for node_mapping in reconciliation:
        parasite, host = node_mapping
        host_parent = parent[host]
        # get the event corresponding to this node mapping
        event_tuple = reconciliation[node_mapping][0]
        event_type = event_tuple[0]
        # if event type is a loss, the parasite is not actually mapped to the host in final 
        # reconciliation, so we skip the node_mapping
        if event_type == 'L':
            continue
        # if the node_mapping is not a leaf_mapping, we add the first relation
        if event_type != 'C':
            temporal_graph[(parasite, TreeType.PARASITE)].append((host, TreeType.HOST))
        # if the node_mapping is not a mapping onto the root of host tree, we add the second relation
        if host_parent != 'Top':
            temporal_graph[(host_parent, TreeType.HOST)].append((parasite, TreeType.PARASITE))
        
        # if event is a transfer, then we add two more temporal relations
        if event_type == 'T':
            # get the mapping for the right child which is the transferred child
            right_child_mapping = event_tuple[2]
            right_child_parasite, right_child_host = right_child_mapping
            # since a transfer event is horizontal, we have these two implied relations
            temporal_graph[(parent[right_child_host], TreeType.HOST)].append((parasite, TreeType.PARASITE))
            # the second relation is only added if the right child mapping is not a leaf mapping
            if right_child_mapping not in reconciliation or reconciliation[right_child_mapping][0][0]!='C':
                temporal_graph[(right_child_parasite, TreeType.PARASITE)].append((host, TreeType.HOST))

    for node_tuple in temporal_graph:
        # we need to make sure the associated value in the dictionary does not contain repeated node tuples
        temporal_graph[node_tuple] = uniquify(temporal_graph[node_tuple])
    return temporal_graph
    
# This is a topological sort based on depth-first-search 
# https://en.wikipedia.org/wiki/Topological_sorting#Depth-first_search
def topological_order(temporal_graph):
    """
    :param temporal graph: as described in the return type of build_temporal_graph
    :return: A dictionary in which a key is a node tuple (name, type) as described
        in build_temporal_graph and the value is a positive integer representing its topological ordering.
        The ordering numbers are consecutive values beginning at 1.
        If the graph has a cycle and the topological ordering therefore fails, this
        function returns None.
    """
    # the ordering of nodes starts at 1
    next_order = 1
    unvisited_nodes = set(temporal_graph.keys())
    # the visitng_nodes is used to detect cycles. If the visiting_nodes add an element that is already
    # in the list, then we have found a cycle
    visiting_nodes = set()
    ordering_dict = {}
    while unvisited_nodes:
        start_node = unvisited_nodes.pop()
        has_cycle, next_order = topological_order_helper(start_node, next_order, visiting_nodes,
                               unvisited_nodes, temporal_graph, ordering_dict)
        if has_cycle: return None
    # reverse the ordering of the nodes
    for node_tuple in ordering_dict:
        ordering_dict[node_tuple] = next_order - ordering_dict[node_tuple]
    return ordering_dict 
           
def topological_order_helper(start_node, start_order, visiting_nodes, unvisited_nodes, temporal_graph, ordering_dict):
    """
    :param start_node: is the starting node to explore the temporal_graph
    :param start_order: is the order we start to label the nodes with
    :param visiting_nodes: are nodes that are on the same path and are currently being explored
    :param unvisited_nodes: are nodes in temporal graph that have not been visited
    :param temporal graph: as described in the return type of build_temporal_graph
    :param ordering_dict: is the dictionary that contains labeled node tuples and their ordering as described
            in topological_order
    :return: a Boolean value that denotes whether the part of temporal graph reachable from start_node
             contains a cycle
    :return: the start order to be used by the remaing nodes of temporal graph that have not been labeled
    """
    next_order = start_order
    is_leaf = start_node not in temporal_graph
    if is_leaf:
        return False, next_order
    else:
        has_cycle = start_node in visiting_nodes
        if has_cycle:
            return True, next_order
        visiting_nodes.add(start_node)
        child_nodes = temporal_graph[start_node]
        for child_node in child_nodes:
            # if the child_node is already labeled, we skip it
            if child_node in ordering_dict:
                continue
            if child_node in unvisited_nodes:
                unvisited_nodes.remove(child_node)
            has_cycle_child, next_order = topological_order_helper(child_node, next_order,  visiting_nodes,
                                   unvisited_nodes, temporal_graph, ordering_dict)
            # if we find a cycle, we stop the process
            if has_cycle_child: return True, next_order
        # if children are all labeled, we can label the start_node
        visiting_nodes.remove(start_node)
        ordering_dict[start_node] = next_order
        return False, next_order + 1

def populate_nodes_with_order(tree_node, tree_type, ordering_dict, leaf_order):
    """
    :param tree_node: the root node of the subtree we want to populate the temporal order information
    :param tree_type: the type of the tree
    :param ordering_dict: a dictionary that maps node tuples to their temporal order as described in topological_order
    :param leaf_order: the temporal order we should assign to the leaves of the tree
    """
    layout = NodeLayout()
    if tree_node.is_leaf:
        layout.col = leaf_order
        tree_node.layout = layout
    else:
        node_tuple = (tree_node.name, tree_type)
        layout.col = ordering_dict[node_tuple]
        tree_node.layout = layout
        populate_nodes_with_order(tree_node.left_node, tree_type, ordering_dict, leaf_order)
        populate_nodes_with_order(tree_node.right_node, tree_type, ordering_dict, leaf_order)


# _get_names_of_internal_nodes(host_tree) will return [m0, m2]
#  _get_names_of_internal_nodes(parasite_tree) will return [n0, n2]

def _get_names_of_internal_nodes(tree):
    """
    :param: A host or parasite tree
    :return: A list of the names (strings) of the internal nodes in that tree
    """
    node_names = list()
    for edge_name in tree:
        edge_four_tuple = tree[edge_name]
        if not _is_leaf_edge(edge_four_tuple):
            node_names.append(_bottom_node(edge_four_tuple))
    return node_names

def _top_node(edge_four_tuple):
    """
    :param: 4-tuple of the form (top_vertex_name, bottom_vertex_name, child_edge1, child_edge2)
    :return: top_vertex_name
    """
    return edge_four_tuple[0]

def _bottom_node(edge_four_tuple):
    """
    :param: 4-tuple of the form (top_vertex_name, bottom_vertex_name, child_edge1, child_edge2)
    :return: bottom_vertex_name
    """
    return edge_four_tuple[1]

def _is_leaf_edge(edge_four_tuple):
    """
    :param: 4-tuple of the form (top_vertex_name, bottom_vertex_name, child_edge1, child_edge2)
    :return: True if child_edge1 = child_edge2 = None.
        This signifies that this edge terminates at a leaf. 
    """
    return edge_four_tuple[3] == None
