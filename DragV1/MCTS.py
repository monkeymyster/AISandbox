from math import *
import random
import time
from timeit import default_timer
import corridormap
import scipy.spatial
import itertools
import networkx as nx
import copy
from api.vector2 import Vector2


class GameState:
    def __init__(self, level, clone=False):
        if clone:
            self.level = level
            self.verbose = False
        else:
            self.iterations = 0
            self.level = level
            self.verbose = False
            self.positions = []
            self.corridor_graph = corridormap.build_graph(level.blockHeights, level.width, level.height)
            self.kdtree = scipy.spatial.cKDTree([self.corridor_graph.node[n]["position"] for n in self.corridor_graph.nodes()])
            self.lookup = [[None for y in range(level.height)] for x in range(level.width)]
            node_count = len(self.corridor_graph.nodes())
            for x, y in itertools.product(range(level.width), range(level.height)):
                closest = None
                for d, i in zip(*self.kdtree.query((x, y), 2, distance_upper_bound=8.0)):
                    if i >= node_count:
                        continue
                    if closest is None or d < closest:
                        self.lookup[x][y] = i
                        closest = d
            self.explored = [False for x in range(len(self.corridor_graph.nodes()))]
            # Initialise the seen grids to false.
            self.seen = [ [False for y in range(level.height)] for x in range(level.width)]
            # Initialise the visibility to false.
            self.visibility = [ [False for y in range(level.height)] for x in range(level.width)]

    def SetInitialPositions(self, bot_positions):
        # We initialise the state to the current location of all the bots.
        for coordinates in bot_positions:
            node_index = self.lookup[int(coordinates.x)][int(coordinates.y)]
            self.positions.append(node_index)
            self.explored[node_index] = True

    def Clone(self):
        # Create a new ticTacToe sate
        clone = GameState(self.level, clone=True)
        clone.corridor_graph = self.corridor_graph
        clone.explored = self.explored[:]
        clone.kdtree = self.kdtree
        clone.positions = self.positions[:]
        clone.visibility = self.visibility[:]
        clone.seen = self.seen[:]
        clone.lookup = self.lookup
        clone.iterations = copy.copy(self.iterations)

        return clone

    def PrintState(self):
        print 'Printing game state!!!!'
        for x in self.positions:
            print x

    def DoMoves(self, moves):
        """ Update the state of the game given a player move
        """
        self.positions = moves
        for x in self.positions:
            self.explored[x] = True
        self.iterations += 1

    def GetMoves(self):
        # The current state.
        # Set a threshold distance of 8. We only consider moves this close.
        moves = []
        choices_list = []
        for x in self.positions:
            neighbours = self.corridor_graph.neighbors(x)
            choices_list.append(neighbours)
        moves = itertools.product(choices_list[0], choices_list[1], choices_list[2], choices_list[3])
        moves = list(moves)

        # Once we have chosen all the moves we want to do them
        if self.verbose:
            print 'The chosen moves are: '
            for x in moves:
                print moves

        return moves

    def GetResult(self):
        """
        Use heuristic knowledge later.
        """
        total = 0
        for node in self.corridor_graph.nodes():
            if self.explored[node]:
                total = total + 1
        return total / self.iterations

class Node:
    def __init__(self, moves = None, parent = None, state = None):
        self.moves = moves # the move that got us to this node - "None" for the root node
        self.parentNode = parent # "None" for the root node
        self.childNodes = []
        self.score = 0
        self.visits = 0
        self.untriedMoves = state.GetMoves() # future child nodes

    def UCTSelectChild(self):
        """ Use the UCB1 formula to select a child node. Often a constant UCTK is applied so we have
            lambda c: c.wins/c.visits + UCTK * sqrt(2*log(self.visits)/c.visits to vary the amount of
            exploration versus exploitation.
        """
        #print "Calling UTCSelectChild"
        s = sorted(self.childNodes, key = lambda c: c.score/c.visits + sqrt(2*log(self.visits)/c.visits))[-1]
        return s

    def AddChild(self, m, s):
        """ Add a child node to the tree. Remove move from the list of untried moves
        """
        n = Node(moves=m, parent = self, state = s)
        self.untriedMoves.remove(m)
        self.childNodes.append(n)
        return n

    def UpdateResult(self, result):
        self.visits += 1
        self.score += result

def UCT(rootstate, itermax, verbose = False):
    """ Conduct a UCT search for itermax iterations starting from rootstate.
        Return the best move from the rootstate.
        Assumes 2 alternating players (player 1 starts), with game results in the range [0.0, 1.0].
    """
    rootnode = Node(state = rootstate)

    for i in range(itermax):
        node = rootnode
        state = rootstate.Clone()

        #Selection
        # While there are no moves left to do and there are child nodes
        # Node is fully expanded and non-terminal
        while node.untriedMoves == [] and node.childNodes != []:
           # print "We've done all the moves performing selection "
            node = node.UCTSelectChild()
            # Update the state given the move to that child node

            state.DoMoves(node.moves)
        # Expansion
        # If we can expand the node
        if node.untriedMoves != []:
            start_time = default_timer()
            m = random.choice(node.untriedMoves)
         #   print m
            # Update the state by doing the move
            state.DoMoves(m)
            # Add the child to the tree and descend
    #        print 'Added child to the tree and decending'
         #   time.sleep(1)
            node = node.AddChild(m, state)
        # Simulation
        counter = 0
        while counter < 20: # while state is non-terminal
            state.DoMoves(random.choice(state.GetMoves()))
            counter = counter + 1
        while node != None:
        #    print "Running back-propagation"
            node.UpdateResult(state.GetResult())
            node = node.parentNode
    # return the move that was most visited
    return sorted(rootnode.childNodes, key = lambda c: c.visits)[-1].moves
