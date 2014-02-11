import math
import numpy
import mahotas
from PIL import Image
from PIL import ImageOps
import networkx as nx

DEFAULT_MAP_SCALE = 10
LONG_EDGE_SPLIT_TOLERANCE_PX = 4.0
WELD_TOLERANCE_PX = 2.0

def build_graph(block_heights, width, height):
    # Create boolean array representation of the map.
    map_image = image_from_block_heights(block_heights, width, height)
    # Create a skeletonised version of the image represented as a boolean array.
    skeleton_map = compute_skeleton_map(map_image)
    # Returns a list of nodes and what they are adjacent to.
    area_graph_adjacency = build_image_space_area_graph(skeleton_map)
    # If there's any long endges, then split them up.
  #  split_long_edges(skeleton_map, area_graph_adjacency, LONG_EDGE_SPLIT_TOLERANCE_PX * DEFAULT_MAP_SCALE)

    weld_vertices(area_graph_adjacency, WELD_TOLERANCE_PX * DEFAULT_MAP_SCALE)
    area_graph_adjacency = convert_to_world_coords(area_graph_adjacency)

    graph = nx.Graph(directed=False)

    for u, coords in enumerate(area_graph_adjacency.keys()):
        graph.add_node(u, position=coords)

    for u, u_coords in enumerate(area_graph_adjacency.keys()):
        for v_coords in area_graph_adjacency[u_coords]:
            v = area_graph_adjacency.keys().index(v_coords)
            graph.add_edge(u, v, weight=math.sqrt((u_coords[0] - v_coords[0])**2 + (u_coords[1] - v_coords[1])**2))

    return graph



# Converts an image into a numpty array and returns it.
def convert_image(img):
    img = img.convert("F")
    return numpy.array(img)


def image_from_block_heights(block_heights, width, height, scale=DEFAULT_MAP_SCALE):
    """
    Returns a boolean array representation of the map. Where 0 represents an impassible object
    such as the edge of the map or a block.
    """

    # Create a new image object using mode I (integer representation) with the specified dimensions.
    # We specify the colour as 1. That is black.
    img = Image.new('I', (width, height), 1)

    # For each pixel in the image check if there is a block in that location.
    # If there is set that pixel colour to white.
    # This results in a binary representation of the blocks.
    for x in range(width):
        for y in range(height):
            if block_heights[x][y] > 0:
                img.putpixel((x,y), 0)

    # We add a border to the image to represent the boundry of the map.
    img = ImageOps.expand(img, border=1, fill=0)

    # The image is the scaled up to the correct size, such that it maps onto the level correctly.
    img = img.resize((scale * img.size[0], scale * img.size[1]), Image.NEAREST)
    # Convert the image in to an array representation of return one of type bool
    image_array = convert_image(img)
    return image_array.astype(numpy.bool)

def compute_skeleton_map(boolean_map):
    """
    Returns a skeletonised version of a binary image via thinning.
    This makes use of the mahotas library.
    """
    return mahotas.thin(boolean_map)

def build_image_space_area_graph(skeleton_map):
    # Return the sets of co-ordinates where there isn't a block or border.
    initial = numpy.where(skeleton_map == 1)

    # If either of the arrays are empty then something went wrong.
    if initial[0].size == 0 or initial[1].size == 0:
        return None

    # We initialise the stack with the starting x and y co-ordinates.
    # We also set the junction to none to begin with.
    stack = [((initial[0][0], initial[1][0]), None)]

    # We want to keep track of the visited co-ordinates. We use sets for easy membership checking.
    visited = set([])

    # We store adjacent nodes as a dictionary.
    # Each node will have an array of adjacent nodes.
    adjacency_list = {None:[]}

    # The possible set of walking directions we could take. Right, Left, Up, Down
    walking_directions = [(1,0), (-1, 0), (0, 1), (0, -1)]

    # Repeat this until the stack is empty.
    while len(stack) > 0:
        # Take the item of the top of the stack.
        top = stack.pop()

        node, junction = top

        # We then add this node to the list of visited nodes.
        visited.add(node)

        children = []

        # For each walking direction we could take from the current node.
        for walking_direction in walking_directions:
            # The child is the position of the current node + the walking direction we
            # move in.
            child = (node[0] + walking_direction[0], node[1] + walking_direction[1])

            # If the location of the child is not clear, then we give up on this one
            # and move onto the next one.
            if skeleton_map[child[0], child[1]] != 1:
                continue

            # If we have visited child then we want to give up.
            # In addition to that, if the child is in the adjacecny list but
            # node in the adjacency list of the current junction then add it.

            if child in visited:
                if child in adjacency_list:
                    if not child in adjacency_list[junction]:
                        adjacency_list[junction].append(child)
                continue

            # If we pass those two criteria then add it to the list of children
            children.append(child)

        # If there are more than two children then we have a jucntion
        if len(children) > 1:
            # Blank the adjacency list
            adjacency_list[node] = []
            # Set it adjacent to the current junction.
            adjacency_list[junction].append(node)
            # Update the junction ato the node.
            junction = node

        # Add the children to the stack and repeat the process.
        for child in children:
            stack.append((child, junction))

    # Delete the invalid None adjacency list
    del adjacency_list[None]

    # Go through the adjacency list and get rid of any duplicates.
    # That is if a node is adjacent to itself.
    for u in adjacency_list.iterkeys():
        adjacency_list[u] = [e for e in adjacency_list[u] if u != e]

        # If a node is in one adjacency list but isn't in that nodes adjacency list
        # put it in there.
        for v in adjacency_list[u]:
            if u not in adjacency_list[v]:
                adjacency_list[v].append(u)

    return adjacency_list
def find_pixel_path(skeleton_map, adjacency_list, u, v):
    """
    Finds the skeleton pixels connecting two junctions
    """
    def reverse_path(begin, end, parents):
        result = [end]
        while result[0] != begin:
            result.insert(0, parents[result[0]])
        return result

    # The possible set of walking directions we could take. Right, Left, Up, Down
    walking_directions = [(1,0), (-1, 0), (0, 1), (0, -1)]

    queue = [u]
    visited = set([])
    parents = {}

    while len(queue) > 0:
        node = queue.pop()

        if node == v:
            return reverse_path(u, v, parents)

        if node != u and node in adjacency_list:
            continue

        for walking_direction in walking_directions:
            child = (node[0] + walking_direction[0], node[1] + walking_direction[1])

            if skeleton_map[child[0], child[1]] != 1:
                continue

            if child in visited:
                continue

            parents[child] = node
            queue.append(child)
    return None

def split_long_edges(skeleton_map, adjacency_list, tolerance):
    # Create the set of all edges in the graph.
    edge_list = set([(u, v) for u in adjacency_list for v in adjacency_list[u]])
    # Keep track of all the edges we've visited.
    visited = set([])
    for (u,v) in edge_list:
        # Check if we've done this edge the other way round.
        if (v,u) in visited:
            continue

        visited.add((u, v))

        # If the distance between the two nodes is greater than the tolerance level.
        if (v[0]-u[0] ** 2) + (v[1] - u[1] ** 2) > tolerance * tolerance:
            path = find_pixel_path(skeleton_map, adjacency_list, u, v)

            if path == None:
                continue

            s = u

            for w in path[1:-1]:
                 if (w[0]-s[0])**2 + (w[1]-s[1])**2 > tolerance * tolerance:
                    adjacency_list[s].remove(v)
                    adjacency_list[v].remove(s)
                    adjacency_list[s].append(w)
                    adjacency_list[v].append(w)
                    adjacency_list[w] = [s, v]
                    s = w

def weld_vertices(adjacency_list, tolerance):
    """
    Remove the vertices that are closer than tolerance.
    """
    cell_size = 10.0 * tolerance
    num_buckets = 128
    buckets = [[] for i in range(num_buckets)]

    def cell_hash(x, y):
        return (0x8da6b343 * x + 0xd8163841 * y) % num_buckets

    def get_weld_vertex(v, bucket):
        for u in buckets[bucket]:
            if (u[0]-v[0])**2 + (u[1]-v[1])**2 < tolerance * tolerance:
                return u

        return None

    def add_to_bucket(v):
        x = int(v[0]/cell_size)
        y = int(v[1]/cell_size)
        buckets[cell_hash(x, y)].append(v)

    def weld_vertex(v):
        top = int((v[1] - tolerance)/cell_size)
        left = int((v[0] - tolerance)/cell_size)
        right = int((v[0] + tolerance)/cell_size)
        bottom = int((v[1] + tolerance)/cell_size)

        visited = set([])

        for i in range(left, right+1):
            for j in range(top, bottom+1):
                bucket = cell_hash(i, j)
                if bucket in visited:
                    continue
                visited.add(bucket)

                w = get_weld_vertex(v, bucket)

                if w:
                    return w

        add_to_bucket(v)
        return v

    def weld(adj_list, v, w):
        w_neis = [e for e in adj_list[w] if e != v]
        v_neis = [e for e in adj_list[v] if e != w]

        adj_list[w] = list(set(w_neis + v_neis))

        for v_nei in v_neis:
            adj_list[v_nei] = [e for e in adj_list[v_nei] if e != v and e != w] + [w]

        del adj_list[v]

    # Vertices is the list of all nodes.
    vertices = adjacency_list.keys()

    # For each node.
    for v in vertices:
        # Weld it.
        w = weld_vertex(v)
        # If this process has made a difference
        if w != v:

            weld(adjacency_list, v, w)

def compute_vertex_areas(input_map, adj_list):
    '''Computes the image map containing pixel-vertex relation'''
    surface = numpy.ones(input_map.shape, dtype=numpy.uint32)
    markers = numpy.zeros(input_map.shape, dtype=numpy.uint32)

    vertex_list = []

    for index, (x, y) in enumerate(adj_list.iterkeys()):
        markers[x, y] = index + 1
        vertex_list.append((x, y))

    return mahotas.cwatershed(surface, markers), vertex_list

def downscale_vertex_areas(vertex_areas_map, scale=DEFAULT_MAP_SCALE):
    m = vertex_areas_map.astype(numpy.uint32)
    i = Image.fromstring('I', (m.shape[1], m.shape[0]), m.tostring())
    i = i.resize((m.shape[1]/scale, m.shape[0]/scale), Image.NEAREST)
    r = numpy.array(i)
    return r

def image_map_to_world_space(coords, scale=DEFAULT_MAP_SCALE, border_width=1):
    x = (coords[1] - border_width * scale)/float(scale)
    y = (coords[0] - border_width * scale)/float(scale)
    return (x, y)

def convert_to_world_coords(adj_list, scale=DEFAULT_MAP_SCALE, border_width=1):
    '''Image space adj list -> world space adj list'''
    result = {}

    for u_coords, neis in adj_list.iteritems():
        u = image_map_to_world_space(u_coords, scale, border_width)
        result[u] = []

        for v_coords in neis:
            result[u].append(image_map_to_world_space(v_coords, scale, border_width))

    return result