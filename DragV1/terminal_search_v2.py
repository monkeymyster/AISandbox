import corridormap
import itertools
import monte_carlo_tree_search_single
from timeit import default_timer

from api import commander
from api import orders
from api.vector2 import Vector2

from tools import visualizer
from PySide import QtGui
import scipy.spatial

class SearchAndDestroy():

    def initialize(self):
        # Generate our corridor map, capturing useful information out of the map
        self.corridor_graph = corridormap.build_graph(self.level.blockHeights, self.level.width, self.level.height)

        # We use scipy to perform a nearest neighbour look-up.
        # This allows use to work out which node the bots are closest to.
        self.kdtree = scipy.spatial.cKDTree([self.corridor_graph.node[n]["position"]
                                             for n in self.corridor_graph.nodes()])

        # Using the nearest neighbour tree. For each grid block, which is 1m x 1m, what is the closest node.
        self.lookup = [[None for y in range(self.level.height)] for x in range(self.level.width)]
        node_count = len(self.corridor_graph.nodes())
        for x, y in itertools.product(range(self.level.width), range(self.level.height)):
            closest = None
            for d, i in zip(*self.kdtree.query((x, y), 2, distance_upper_bound=8.0)):
                if i >= node_count:
                    continue
                if closest is None or d < closest:
                    self.lookup[x][y] = i
                    closest = d

        self.terminal_nodes = []
        for node in self.corridor_graph.nodes():
            # If only one neighbor then it's a terminal node.
            if len(self.corridor_graph.neighbors(node)) == 1:
                self.terminal_nodes.append(node)


        # Initialise all nodes to not having been visited.
        self.explored = [False for x in range(len(self.corridor_graph.nodes()))]

        self.initialise = True

    def issue_move(self, bot, move):
        pos = self.corridor_graph.node[move]["position"]
        pos = Vector2(pos[0], pos[1])
        self.issue(orders.Charge, bot, pos)
        self.explored[move] = True

    def nearest_unexplored_root_node(self, bot_position):
        closest_node = None
        closest_distance = 1000000
        for node in self.terminal_nodes:
            if self.explored[node] == False:
                node_pos = self.corridor_graph.node[node]["position"]
                node_pos = Vector2(node_pos[0], node_pos[1])
                distance = bot_position.distance(node_pos)
                if distance < closest_distance:
                    closest_distance = distance
                    closest_node = node
        if closest_node == None:
            return 1
        return closest_node



    def tick(self):
        """
        Called at each iteration of the game.
        """
        for bot in self.game.bots_available:
            node = self.nearest_unexplored_root_node(bot.position)
            self.issue_move(bot, node)

