class SimulationDashboard:
    """Displays live team and explorer information."""

    def __init__(
        self,
        env,
        explorers,
        team_storages,
        team_knowledge_boards,
        event_logger,
    ):
        self.env = env
        self.explorers = explorers
        self.team_storages = team_storages
        self.team_knowledge_boards = team_knowledge_boards
        self.event_logger = event_logger

        self.selected_explorer = (
            explorers[0] if explorers else None
        )

        self.draw()

    def select_explorer(self, explorer_name):
        """Select an explorer for inspection."""

        for explorer in self.explorers:
            if explorer.name == explorer_name:
                self.selected_explorer = explorer
                return

    def draw_text(self, text, x, y, fontsize=12, color="#FFFFFF"):
        """Draw a static dashboard label."""

        return self.env.AnimateText(
            text=text,
            x=x,
            y=y,
            fontsize=fontsize,
            textcolor=color,
            layer=11,
            screen_coordinates=True,
        )

    def draw(self):

        # Dashboard background.
        self.env.AnimateRectangle(
            spec=(665, 50, 900, 480),
            fillcolor="#24485B",
            linecolor="#52798A",
            linewidth=2,
            layer=12,
            screen_coordinates=True,
        )

        # Main heading.
        self.draw_text(
            "ISLAND SURVIVORS",
            670,
            465,
            fontsize=22,
            color="#F4EBD0",
        )

        # --------------------------------------------------
        # TEAM OVERVIEW
        # --------------------------------------------------

        self.draw_text(
            "TEAM OVERVIEW",
            680,
            431,
            fontsize=14,
            color="#E9C879",
        )

        self.env.AnimateText(
            text=lambda: self.team_overview_text(),
            x=670,
            y=410,
            fontsize=11,
            textcolor="#FFFFFF",
            layer=11,
            screen_coordinates=True,
        )

        # --------------------------------------------------
        # EXPLORER SELECTION
        # --------------------------------------------------

        self.draw_text(
            "SELECT EXPLORER",
            670,
            400,
            fontsize=14,
            color="#E9C879",
        )

        # Create two rows of clickable explorer buttons.
        for index, explorer in enumerate(self.explorers):

            column = index % 2
            row = index // 2

            x = 725 + column * 115
            y = 340 - row * 34

            self.env.AnimateButton(
                x=x,
                y=y,
                width=95,
                text=explorer.name,
                fillcolor=explorer.color,
                color="#FFFFFF",
                fontsize=11,
                action=lambda name=explorer.name: (
                    self.select_explorer(name)
                ),
                env=self.env,
            )

        # --------------------------------------------------
        # SELECTED EXPLORER
        # --------------------------------------------------

        self.draw_text(
            "EXPLORER INSPECTOR",
            680,
            340,
            fontsize=14,
            color="#E9C879",
        )

        self.env.AnimateText(
            text=lambda: self.selected_explorer_text(),
            x=680,
            y=315,
            fontsize=11,
            textcolor="#FFFFFF",
            layer=11,
            screen_coordinates=True,
        )

        # --------------------------------------------------
        # TEAM STORAGE
        # --------------------------------------------------

        self.draw_text(
            "TEAM STORAGE",
            680,
            205,
            fontsize=14,
            color="#E9C879",
        )

        self.env.AnimateText(
            text=lambda: self.storage_text(),
            x=680,
            y=180,
            fontsize=11,
            textcolor="#FFFFFF",
            layer=11,
            screen_coordinates=True,
        )

        # --------------------------------------------------
        # RECENT EVENTS
        # --------------------------------------------------

        self.draw_text(
            "RECENT EVENTS",
            680,
            135,
            fontsize=14,
            color="#E9C879",
        )

        self.env.AnimateText(
            text=lambda: self.recent_events_text(),
            x=680,
            y=112,
            fontsize=9,
            textcolor="#FFFFFF",
            layer=11,
            screen_coordinates=True,
        )

    def team_overview_text(self):
        """Build the live team overview."""

        alive_count = sum(
            explorer.is_alive
            for explorer in self.explorers
        )

        total_count = len(self.explorers)

        selected_team = (
            self.selected_explorer.team_id
            if self.selected_explorer is not None
            else None
        )

        knowledge = self.team_knowledge_boards.get(selected_team)

        known_count = 0

        if knowledge is not None:
            known_count = sum(
                resource["quantity"] > 0
                for resource in knowledge.known_resources.values()
            )

        return (
            f"Simulation time: {self.env.now():.1f}\n"
            f"Explorers alive: {alive_count}/{total_count}\n"
            f"Known resource sites: {known_count}"
        )

    def selected_explorer_text(self):
        """Build the live selected-explorer information."""

        explorer = self.selected_explorer

        if explorer is None:
            return "No explorer selected."

        status = "ALIVE" if explorer.is_alive else "DEAD"

        inventory = explorer.inventory

        last_decision = self.get_last_decision(explorer.name)

        if last_decision is None:
            action_text = "Not yet decided"
            reason_text = "No decision recorded."
        else:
            action_text = last_decision["message"].replace(
                "Selected action: ",
                "",
            )

            reason_text = next(
                (
                    detail.replace("Reason: ", "")
                    for detail in last_decision["details"]
                    if detail.startswith("Reason:")
                ),
                "No reason recorded.",
            )

        # Keep the reason short enough for the sidebar.
        if len(reason_text) > 38:
            reason_text = reason_text[:35] + "..."

        return (
            f"{explorer.name} | {status} | Team {explorer.team_id}\n"
            f"Position: ({explorer.row}, {explorer.col})\n"
            f"Health: {explorer.health}/100  Hunger: {explorer.hunger}/100\n"
            f"Inventory: W:{inventory.get('wood', 0)} "
            f"S:{inventory.get('stone', 0)} "
            f"B:{inventory.get('berries', 0)}\n"
            f"Action: {action_text}\n"
            f"Reason: {reason_text}"
        )

    def get_last_decision(self, explorer_name):
        """Find the most recent decision made by an explorer."""

        events = self.event_logger.get_recent_events(
            limit=100,
            explorer_name=explorer_name,
            include_debug=True,
        )

        for event in reversed(events):
            if event["event"] == "DECISION":
                return event

        return None

    def storage_text(self):
        """Display storage belonging to the selected explorer's team."""

        if self.selected_explorer is None:
            return "No team selected."

        team_id = self.selected_explorer.team_id

        storage = self.team_storages.get(team_id)

        if storage is None:
            return "Storage unavailable."

        inventory = storage.inventory

        return (
            f"Wood: {inventory.get('wood', 0)}  "
            f"Stone: {inventory.get('stone', 0)}  "
            f"Berries: {inventory.get('berries', 0)}"
        )

    def recent_events_text(self):
        """Display the latest meaningful team events."""

        if self.selected_explorer is None:
            return "No events."

        events = self.event_logger.get_recent_events(
            limit=4,
            team_id=self.selected_explorer.team_id,
            include_debug=False,
        )

        if not events:
            return "Waiting for events..."

        lines = []

        for event in events:

            message = event["message"].replace("\n", " ")

            if len(message) > 27:
                message = message[:24] + "..."

            lines.append(
                f"T={event['time']:.0f} "
                f"{event['explorer']}: "
                f"{event['event']}"
            )

        return "\n".join(lines)