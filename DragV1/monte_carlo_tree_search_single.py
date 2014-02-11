import random
from timeit import default_timer
import itertools
from math import *
import copy

class GameState:
    def __init__(self, bot_position, explored_nodes, corridor_graph, verbose = False):
        # What position are the bots in relative to the nodes?
        self.current_position = bot_position
        # What nodes have we already explored
        self.explored_nodes = explored_nodes
        self.corridor_graph = corridor_graph
        self.verbose = verbose
        self.moves_made = 0
        total = 0
        for node in self.corridor_graph.nodes():
            if self.explored_nodes[node]:
                total = total + 1
        self.number_explored = total

    def clone(self):
        #start_time = default_timer()
        # Create a new ticTacToe sate
        clone = GameState(self.current_position, self.explored_nodes[:], self.corridor_graph)
        clone.moves_made = copy.copy(self.moves_made)
       # print "Clone time ", default_timer() - start_time
        return clone

    def do_moves(self, move):
        #start_time = default_timer()
        """
        Update the state of the game given a player move
        """
        self.current_position = move
        if not self.explored_nodes[self.current_position]:
            self.number_explored += 1
            self.explored_nodes[self.current_position] = True
        self.moves_made += 1
        #print ' Do moves time: ', default_timer() - start_time

    def get_moves(self):
       # start_time = default_timer()
        neighbours = self.corridor_graph.neighbors(self.current_position)
        temp_neighbours = copy.copy(neighbours)
        for n in neighbours:
            if self.explored_nodes[n]:
                temp_neighbours.remove(n)
       # print ' Get moves time: ', default_timer() - start_time
        if len(temp_neighbours) > 0:
            return temp_neighbours
        else:
            return neighbours


    def get_result(self):
        """
        Use heuristic knowledge later.
        """
        if self.number_explored > self.moves_made * 0.9:
            print ' Found a good path'
            return 1.0
        else:
            return 0

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
        #s = sorted(self.child_nodes, key = lambda c: c.score)[-1]
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
           # iter_start_time = default_timer()
            start_time = default_timer()
            # Create a copy of the root node.
            self.node = self.root_node
            # Create a copy of the state from the root state.
            self.state = self.root_state.clone()
          #  print "Initialisation time: ", default_timer() - start_time
            #               Selection                   #
            # Only perform if all the moves from the current state have been explored.

            while self.node.untried_moves == [] and self.node.child_nodes != []:
              #  start_time = default_timer()
               # print "Performing selection"
                self.node = self.node.uct_select_child()
                self.state.do_moves(self.node.move)
             #   print "Selection execution time ", default_timer() - start_time

            #               Expansion                   #
            # If there are moves we can do from the current state.

            if self.node.untried_moves != []:
              #  print "Performing expansion"
             #   start_time = default_timer()
                m = self.state.choose_move(self.node.untried_moves)
                self.state.do_moves(m)
                self.node = self.node.add_child(m, self.state)
             #   print "Expansion execution time :", default_timer() - start_time

            counter = 1
          #  start_time = default_timer()
            while counter < 40:
             #   print "Performing simulation"
                m = self.state.choose_move(self.state.get_moves())
                self.state.do_moves(m)
                counter += 1
          #  print " Simulation execution time: ", default_timer() - start_time
           # start_time = default_timer()

            while self.node != None:
             #   print "Performing back-prop"
                self.node.update_result(self.state.get_result())
                self.node = self.node.parent_node
           # print "Back-prop execution time", default_timer() - start_time
      #  print "The iteration execution time was : ", default_timer() - iter_start_time

    def return_move(self):
        return sorted(self.root_node.child_nodes, key = lambda c: c.visits)[-1].move

