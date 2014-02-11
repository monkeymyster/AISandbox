import math
import random
import itertools
import networkx as nx
import time
from timeit import default_timer

from api import commander
from api import orders
from api.vector2 import Vector2
from tools import visibility
from tools import visualizer
import scipy.spatial
from PySide import QtGui, QtCore
import corridormap
import MCTS


## Sample Commander for the Operation Dragnet Challenge.

#class SearchAndDestroy(commander.Commander):
class SearchAndDestroy():
    # Any initialisation that needs to be done at the start of the game is done here.
    def initialize(self):


        self.window = visualizer.VisualizerWindow(self)
        self.window.drawBots = True
        self.iterations = 0

        # We use this so that we can initialise the game state once we have access to bot information.
        self.initialise_bots = True
        # Initialise the game state.
        self.game_state = MCTS.GameState(self.level)

    def IssueMoves(self, move):
        i = 0
      #  print 'Issuing orders'
        for bot in self.game.bots_available:
        #    print ' Issuing order to bot ' ,bot.name
         #   print ' Move from ', self.game_state.lookup[int(bot.position.x)][int(bot.position.y)], 'to ', move[i]
            pos = self.game_state.corridor_graph.node[move[i]]["position"]
            pos = Vector2(pos[0], pos[1])
            self.issue(orders.Charge, bot, pos)
            i = i + 1

    ## Here you put the main AI logic of your commander.
    def tick(self):
        # At the start of the tick we update the state so the MCTS is
        # aware of the current bot positions.
        if self.initialise_bots == True:
            bot_positions = []
            for bot in self.game.bots_available:
                bot_positions.append(bot.position)
            self.game_state.SetInitialPositions(bot_positions)
            self.initialise_bots = False

        if len(self.game.bots_available) == 4:
       #     start_time = default_timer()
            m = MCTS.UCT(rootstate = self.game_state, itermax = 10000, verbose = False)
            # Once we have the best move we issue it to any bots that are available.
            self.game_state.DoMoves(m)
            self.IssueMoves(m)
       #     print default_timer() - start_time

        total = 0
        for node in self.game_state.corridor_graph.nodes():
            if self.game_state.explored[node] == True:
                total = total + 1
       # print 'Iterations ', self.iterations
       # print ' The total number of nodes visited is:'
       # print total
        self.iterations += 1
        #for bot in self.game.bots_alive:
        #    self.rasterizeVisibility(bot.position, bot.facingDirection)

        #for bot in self.game.bots_available:
        #    pos = self.level.findRandomFreePositionInBox(self.level.area)
        #    self.issue(orders.Charge, bot, pos)

        self.window.dirty = True
        self.window.update()

    # Calculate the visibility gained given a particular position and facing direciton.
    def rasterizeVisibility(self, position, facing_direction):
        fov = math.pi * 0.5
        fov = fov * 0.9
        coshalffov = math.cos(fov * 0.5)

        def setVisible(x, y):
            d = (Vector2(x, y) - position).normalized()
            dp = d.dotProduct(facing_direction)

            if dp > coshalffov:
                self.game_state.visibility[x][y] = True
                node_index = self.game_state.lookup[x][y]

                if not self.game_state.seen[x][y]:
                    self.game_state.seen[x][y] = True
                    #self.corridor_graph.node[node_index]["seen_count"] += 1

        wave = visibility.Wave((0, 0, self.level.width, self.level.height), isBlocked=lambda x, y: self.level.blockHeights[x][y] > 1, setVisible=setVisible)
        wave.compute(position)

    def postWorldHook(self, visualizer):
        for s, f in self.game_state.corridor_graph.edges():
            visualizer.drawLine(self.game_state.corridor_graph.node[s]["position"], self.game_state.corridor_graph.node[f]["position"], QtGui.qRgb(255, 255, 255))

        for n in self.game_state.corridor_graph.nodes():
            visualizer.drawCircle(self.game_state.corridor_graph.node[n]["position"], QtGui.qRgb(255, 255, 255))
            if self.game_state.explored[n]:
                visualizer.drawCircle(self.game_state.corridor_graph.node[n]["position"], QtGui.qRgb(0, 0, 0), scale=0.8)

    ## Called once when the match ends.
    def shutdown(self):
        pass
