class TeamKnowledge:
    """Stores information shared between members of a team."""

    def __init__(self, team_id):
        self.team_id = team_id

        # Resources discovered by team members.
        # Key: (row, col)
        self.known_resources = {}

    def update_resource(
        self,
        resource,
        discovered_by,
        observed_at,
    ):
        """Publish or update a resource discovery."""

        position = tuple(resource["position"])

        existing = self.known_resources.get(position)

        if existing is None:

            # First discovery of this resource.
            self.known_resources[position] = {
                "kind": resource["kind"],
                "resource_type": resource["resource_type"],
                "position": position,
                "quantity": resource["quantity"],

                "discovered_by": discovered_by,
                "first_discovered_at": observed_at,

                "last_observed_by": discovered_by,
                "last_observed_at": observed_at,
            }

        else:

            # Update the existing knowledge.
            existing.update({
                "kind": resource["kind"],
                "resource_type": resource["resource_type"],
                "quantity": resource["quantity"],

                "last_observed_by": discovered_by,
                "last_observed_at": observed_at,
            })

    def get_resources(self):
        """Return a snapshot of the team's known resources."""

        return [
            resource.copy()
            for resource in self.known_resources.values()
        ]