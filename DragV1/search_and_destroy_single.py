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
        """
        Called at the start of the game. Any heavy computation should be carried out here to save time later on.
        Here we construct the corridor map.
        """
        # Set parameters for visualisation
        self.window = visualizer.VisualizerWindow(self)
        self.window.drawBots = True
        self.game_state_updated = True

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

        # Initialise all nodes to not having been visited.
        self.explored = [False for x in range(len(self.corridor_graph.nodes()))]

        self.initialise = True

    def issue_moves(self, bot, move):
        pos = self.corridor_graph.node[move]["position"]
        pos = Vector2(pos[0], pos[1])
        self.issue(orders.Charge, bot, pos)

    def tick(self):
        """
        Called at each iteration of the game.
        """
        # We only set up the game state once. We have to do it in here because the bots aren't originally available.
        if self.initialise:
            bots = self.game.team.members
            self.bot_name = bots[0].name
            pos = self.game.bots[self.bot_name].position
            pos = self.lookup[int(pos.x)][int(pos.y)]
            self.game_state = monte_carlo_tree_search_single.GameState(pos,self.explored,self.corridor_graph)
            self.initialise = False
            self.game_state_updated = True

        for bot in self.game.bots_available:
            if bot.name == self.bot_name and not self.game_state_updated:
                # Calculate what set of moves we want to take.
                m = self.mcts.return_move()
                self.issue_moves(bot, m)
                self.game_state.do_moves(m)
                self.game_state_updated = True

        if self.game_state_updated:
            self.mcts = monte_carlo_tree_search_single.UCT(root_state = self.game_state, max_iterations=20)
            self.mcts.run_mcst()
            self.game_state_updated = False
        else:
            self.mcts.run_mcst()

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
            #visualizer.drawCircle(self.corridor_graph.node[n]["position"],
            #                      QtGui.qRgb(255, 255, 255))
            pos = self.corridor_graph.node[n]["position"]
            pos = Vector2(pos[0], pos[1])
            visualizer.drawText(pos, QtGui.qRgb(255, 255, 255), unicode(n))
            #if self.explored[n]:
                #visualizer.drawCircle(self.corridor_graph.node[n]["position"],
                                     # QtGui.qRgb(0, 0, 0), scale=0.8)

        height_separator = self.level.height / 2
        width_separator = self.level.width / 2

        graph_one = []
        graph_two = []
        graph_three = []
        graph_four = []
        for n in self.corridor_graph.nodes():
            position = self.corridor_graph.node[n]["position"]
            position = Vector2(position[0], position[1])
            if position.y > height_separator:
                if position.x > width_separator:
                    graph_one.append(n)
                else:
                    graph_two.append(n)
            else:
                if position.x > width_separator:
                    graph_three.append(n)
                else:
                    graph_four.append(n)

        graph_one = self.corridor_graph.subgraph(graph_one)
        for n in graph_one.nodes():
            visualizer.drawCircle(self.corridor_graph.node[n]["position"], QtGui.qRgb(255, 0, 0), scale=0.8)