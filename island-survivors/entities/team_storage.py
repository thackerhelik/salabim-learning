class TeamStorage:

    def __init__(self, team_id, row, col):
        self.team_id = team_id
        self.row = row
        self.col = col

        self.inventory = {
            "wood": 0,
            "stone": 0,
            "berries": 0,
        }