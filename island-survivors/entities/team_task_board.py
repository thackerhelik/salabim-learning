class TeamTaskBoard:
    """Manages task assignments and resource reservations for a team."""

    def __init__(self, team_id):
        self.team_id = team_id

        # Key: resource position
        # Value: task ownership information
        self.resource_claims = {}

    def cleanup_expired_claims(self, current_time):
        """Remove claims that have expired."""

        expired_positions = [
            position
            for position, claim in self.resource_claims.items()
            if claim["expires_at"] <= current_time
        ]

        for position in expired_positions:
            del self.resource_claims[position]

    def claim_resource(
        self,
        position,
        explorer_name,
        current_time,
        lease_duration=5,
    ):
        """Reserve a resource for an explorer."""

        position = tuple(position)

        self.cleanup_expired_claims(current_time)

        existing_claim = self.resource_claims.get(position)

        # Another explorer already owns this task.
        if (
            existing_claim is not None
            and existing_claim["assigned_to"] != explorer_name
        ):
            return False

        # Create or renew the claim.
        self.resource_claims[position] = {
            "assigned_to": explorer_name,
            "claimed_at": current_time,
            "expires_at": current_time + lease_duration,
        }

        return True

    def get_resource_claims(self, current_time):
        """Return a snapshot of active resource claims."""

        self.cleanup_expired_claims(current_time)

        return {
            position: claim.copy()
            for position, claim in self.resource_claims.items()
        }

    def is_claimed_by_other(
        self,
        position,
        explorer_name,
        current_time,
    ):
        """Check whether another explorer owns a resource claim."""

        self.cleanup_expired_claims(current_time)

        claim = self.resource_claims.get(tuple(position))

        return (
            claim is not None
            and claim["assigned_to"] != explorer_name
        )

    def release_resource(self, position, explorer_name):
        """Release a resource claim owned by an explorer."""

        position = tuple(position)

        claim = self.resource_claims.get(position)

        if (
            claim is not None
            and claim["assigned_to"] == explorer_name
        ):
            del self.resource_claims[position]
            return True

        return False

    def release_all(self, explorer_name):
        """Release all resource claims owned by an explorer."""

        positions = [
            position
            for position, claim in self.resource_claims.items()
            if claim["assigned_to"] == explorer_name
        ]

        for position in positions:
            del self.resource_claims[position]
