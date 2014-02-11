from api import commander
from api import orders

class SearchAndDestroy(commander.Commander):
    # Any initialisation that needs to be done at the start of the game is done here.
    def initialize(self):
        pass
    
    ## Here you put the main AI logic of your commander.
    def tick(self):
        for bot in self.game.bots_available:
            pos = self.level.findRandomFreePositionInBox(self.level.area)
            self.issue(orders.Charge, bot, pos)

    ## Called once when the match ends.
    def shutdown(self):
        pass
