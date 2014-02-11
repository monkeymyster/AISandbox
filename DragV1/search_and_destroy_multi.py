import corridormap
import itertools
import monte_carlo_tree_search_multi
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

    def issue_moves(self, move):
        move_index = 0
        for bot in self.game.bots_available:
            pos = self.corridor_graph.node[move[move_index]]["position"]
            pos = Vector2(pos[0], pos[1])
            self.issue(orders.Charge, bot, pos)
            move_index += 1

    def tick(self):
        """
        Called at each iteration of the game.
        """
        # We only set up the game state once. We have to do it in here because the bots aren't originally available.
        if self.initialise:
            self.bot_positions = []
            for bot in self.game.bots_available:
                self.bot_positions.append(self.lookup[int(bot.position.x)][int(bot.position.y)])
            print "The bot positions are ", self.bot_positions
            self.game_state = monte_carlo_tree_search_multi.GameState(self.bot_positions,self.explored,self.corridor_graph)
            self.initialise = False
            self.game_state_updated = True

        if len(self.game.bots_available) == 4 and not self.game_state_updated:
            # Calculate what set of moves we want to take.
            m = self.mcts.return_move()
            self.issue_moves(m)
            self.game_state.do_moves(m)
            self.game_state_updated = True

        if self.game_state_updated:
            self.mcts = monte_carlo_tree_search_multi.UCT(root_state = self.game_state, max_iterations=100)
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
            visualizer.drawCircle(self.corridor_graph.node[n]["position"],
                                  QtGui.qRgb(255, 255, 255))
            if self.explored[n]:
                visualizer.drawCircle(self.corridor_graph.node[n]["position"],
                                      QtGui.qRgb(0, 0, 0), scale=0.8)
