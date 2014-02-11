import corridormap
import itertools
import monte_carlo_tree_search_terminal

from api import commander
from api import orders
from api.vector2 import Vector2

from tools import visualizer
from PySide import QtGui
import scipy.spatial
import networkx as nx

class SearchAndDestroy(commander.Commander):

    def initialize(self):
        self.window = visualizer.VisualizerWindow(self)
        self.window.drawBots = True

        # Generate our corridor map, capturing useful information out of the map
        self.corridor_graph = corridormap.build_graph(self.level.blockHeights, self.level.width, self.level.height)

        # We use scipy to perform a nearest neighbour look-up.
        # This allows use to work out which node the bots are closest to.
        self.kdtree = scipy.spatial.cKDTree([self.corridor_graph.node[n]["position"]
                                             for n in self.corridor_graph.nodes()])

        for node in self.corridor_graph.nodes():
            self.corridor_graph.node[node]["distances"] = nx.single_source_dijkstra_path_length(self.corridor_graph, node, weight="weight")

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

        # Initialise all nodes to not having been visited.
        self.explored = [False for x in range(len(self.corridor_graph.nodes()))]

        self.terminal_nodes = []
        for node in self.corridor_graph.nodes():
            # If only one neighbor then it's a terminal node.
            if len(self.corridor_graph.neighbors(node)) == 1:
                self.terminal_nodes.append(node)

        self.initialise = True

    def issue_moves(self, move):
        move_index = 0
        for bot in self.game.bots_alive:
            if bot.state == bot.STATE_IDLE:
                pos = self.corridor_graph.node[move[move_index]]["position"]
                pos = Vector2(pos[0], pos[1])
                self.issue(orders.Charge, bot, pos)
            move_index += 1

    def tick(self):
        """
        Called at each iteration of the game.
        """
        if self.initialise:
            self.initialise = False
            self.bot_positions = []
            for bot in self.game.bots_alive:
                self.bot_positions.append(self.lookup[int(bot.position.x)][int(bot.position.y)])
            self.game_state = monte_carlo_tree_search_terminal.GameState(self.bot_positions, self.explored,self.corridor_graph, self.terminal_nodes, self.level)

        if len(self.game.bots_available) > 0:
            self.mcts = monte_carlo_tree_search_terminal.UCT(root_state = self.game_state, max_iterations=1000)
            self.mcts.run_mcst()
            # Calculate what set of moves we want to take.
            m = self.mcts.return_move()
            # We remove any moves that bots cannot make yet and replace with current position
            index = 0
            for bot in self.game.bots_alive:
                if not bot.state == bot.STATE_IDLE:
                    m[index] = self.bot_positions[index]
                index += 1
            self.issue_moves(m)
            self.game_state.do_moves(m)

          # Update the visualisation window
        self.window.dirty = True
        self.window.update()

    def postWorldHook(self, visualizer):
        """
        Will draw a graphical representation of the corridor map on to the
        visualisation window.
        """
        for s, f in self.corridor_graph.edges():
            visualizer.drawLine(self.corridor_graph.node[s]["position"],
                                self.corridor_graph.node[f]["position"],
                                QtGui.qRgb(255, 255, 255))

        for n in self.corridor_graph.nodes():
            visualizer.drawCircle(self.corridor_graph.node[n]["position"],
                                  QtGui.qRgb(255, 255, 255))
            if self.explored[n]:
                visualizer.drawCircle(self.corridor_graph.node[n]["position"],
                                      QtGui.qRgb(0, 0, 0), scale=0.8)
