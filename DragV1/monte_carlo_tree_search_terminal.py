import random
import itertools
import copy
from math import *
from api.vector2 import Vector2

class GameState:
    def __init__(self, bot_positions, explored_nodes, corridor_graph, terminal_nodes, level, verbose = False):
        self.bot_positions = bot_positions
        # What nodes have we already explored
        self.explored_nodes = explored_nodes
        self.corridor_graph = corridor_graph
        self.terminal_nodes = terminal_nodes
        self.distance_travelled = 0
        self.level = level

    def clone(self):
        # Create a new ticTacToe sate
        clone = GameState(copy.copy(self.bot_positions), self.explored_nodes[:], self.corridor_graph, self.terminal_nodes, self.level)
        clone.distance_travelled = copy.copy(self.distance_travelled)
        return clone

    def do_moves(self, moves):
        """
        Update the state of the game given a player move
        """
        total_distance = 0
        for move, pos in zip(moves, self.bot_positions):
            distance = self.corridor_graph.node[pos]["distances"][move]
            total_distance += distance
            self.explored_nodes[move] = True
        self.bot_positions = moves
        self.distance_travelled += total_distance

    def area_check(self, pos):
        width_divide = self.level.width / 2
        height_divide = self.level.height / 2
        if pos.x < width_divide and pos.y > height_divide:
            return 1
        if pos.x > width_divide and pos.y > height_divide:
            return 2
        if pos.x < width_divide and pos.y < height_divide:
            return 3
        if pos.x > width_divide and pos.y < height_divide:
            return 4
        return None

    def get_moves(self):
        moves = []
        i = 1
        for pos in self.bot_positions:
            available_nodes = []
            for node in self.terminal_nodes:
                if not self.explored_nodes[node]:
                    pos = self.corridor_graph.node[node]["position"]
                    pos = Vector2(pos[0], pos[1])
                    if i == self.area_check(pos):
                        available_nodes.append(node)
            i += 1
            if available_nodes == []:
                return [(1,1,1,1)]
            moves.append(available_nodes)
            #moves.append(available_nodes)

        moves = itertools.product(moves[0],moves[1],moves[2],moves[3])
        #moves = itertools.combinations(available_nodes, 4)
        moves = list(moves)
        return moves



    """
    def get_moves(self):
        moves = []
        for pos in self.bot_positions:
            available_nodes = []
            radius = 50
            while available_nodes == [] and radius < 150:
                for node in self.terminal_nodes:
                    distance = self.corridor_graph.node[pos]["distances"][node]
                    if not self.explored_nodes[node] and distance < radius:
                        available_nodes.append(node)
                radius += 50
            if available_nodes == []:
                return [(1,1,1,1)]
            moves.append(available_nodes)
            #moves.append(available_nodes)

        moves = itertools.product(moves[0],moves[1],moves[2],moves[3])
        #moves = itertools.combinations(available_nodes, 4)
        moves = list(moves)
        return moves
        """


    def get_result(self):
        """
        Use heuristic knowledge later.
        """
        return 1000.0/self.distance_travelled

    def choose_move(self, available_moves):
        return random.choice(available_moves)

class Node:
    def __init__(self, move = None, parent = None, state = None):
        self.move = move # the move that got us to this node - "None" for the root node
        self.parent_node = parent # "None" for the root node
        self.child_nodes = []
        self.score = 0
        self.visits = 0
        self.untried_moves = state.get_moves() # future child nodes

    def uct_select_child(self):
        """ Use the UCB1 formula to select a child node. Often a constant UCTK is applied so we have
            lambda c: c.wins/c.visits + UCTK * sqrt(2*log(self.visits)/c.visits to vary the amount of
            exploration versus exploitation.
        """
        s = sorted(self.child_nodes, key = lambda c: c.score/c.visits + sqrt(2*log(self.visits)/c.visits))[-1]
        return s

    def add_child(self, m, s):
        """ Add a child node to the tree. Remove move from the list of untried moves
        """
        n = Node(move=m, parent = self, state = s)
        self.untried_moves.remove(m)
        self.child_nodes.append(n)
        return n

    def update_result(self, result):
        self.visits += 1
        self.score += result


class UCT:
    """ Conduct a UCT search for the maximum iterations starting from the rootstate.
        Return the best move available from the root state given the results.
    """
    def __init__(self, root_state, max_iterations):
        self.root_state = root_state
        self.root_node = Node(state = root_state)
        self.max_iterations = max_iterations

    def run_mcst(self):
        # Repeat for the maximum number of iterations
        for i in range(self.max_iterations):
            # Create a copy of the root node.
            self.node = self.root_node
            # Create a copy of the state from the root state.
            self.state = self.root_state.clone()

            #               Selection                   #
            # Only perform if all the moves from the current state have been explored.

            while self.node.untried_moves == [] and self.node.child_nodes != []:
               # print "Performing selection"
                self.node = self.node.uct_select_child()
                self.state.do_moves(self.node.move)

            #               Expansion                   #
            # If there are moves we can do from the current state.

            if self.node.untried_moves != []:
              #  print "Performing expansion"
                m = self.state.choose_move(self.node.untried_moves)
                self.state.do_moves(m)
                self.node = self.node.add_child(m, self.state)

            while self.state.get_moves() != [(1,1,1,1)]:
             #   print "Performing simulation"
                m = self.state.choose_move(self.state.get_moves())
                self.state.do_moves(m)

            while self.node != None:
             #   print "Performing back-prop"
                self.node.update_result(self.state.get_result())
                self.node = self.node.parent_node

    def return_move(self):
        return list(sorted(self.root_node.child_nodes, key = lambda c: c.visits)[-1].move)

