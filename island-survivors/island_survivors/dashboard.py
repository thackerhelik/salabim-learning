import sys
import tkinter as tk


class SimulationDashboard:
    """Displays live simulation information in a fixed sidebar."""

    MAP_WIDTH = 650
    PANEL_WIDTH = 350
    WINDOW_HEIGHT = 600

    def __init__(
        self,
        env,
        explorers,
        team_storages,
        team_knowledge_boards,
        event_logger,
        map_bounds,
        team_leaders=None,
    ):
        self.env = env
        self.root = env.root
        self.explorers = explorers
        self.team_storages = team_storages
        self.team_knowledge_boards = team_knowledge_boards
        self.event_logger = event_logger
        self.map_bounds = map_bounds
        self.team_leaders = team_leaders or {}

        self._pan_start = None

        self._refresh_job = None
        self._closed = False

        self.selected_explorer = (
            explorers[0] if explorers else None
        )

        self.buttons = {}

        if self.root is None:
            raise RuntimeError(
                "Salabim animation window has not been initialized."
            )

        self.configure_window()
        self.build_widgets()
        self.update_view()
        self.start_refresh()

    def configure_window(self):
        """Create a map canvas and a separate dashboard frame."""

        # Find the Canvas created by Salabim.
        canvases = [
            widget
            for widget in self.root.winfo_children()
            if isinstance(widget, tk.Canvas)
        ]

        if not canvases:
            raise RuntimeError(
                "Could not find Salabim's animation Canvas."
            )

        self.canvas = canvases[0]

        # Reposition the canvas on the left.
        self.canvas.pack_forget()

        self.canvas.configure(
            width=self.MAP_WIDTH,
            height=self.WINDOW_HEIGHT,
            highlightthickness=0,
        )

        self.canvas.pack(
            side=tk.LEFT,
            anchor="nw",
            fill=tk.NONE,
            expand=False,
        )

        # Create a separate, fixed-width sidebar.
        self.panel = tk.Frame(
            self.root,
            width=self.PANEL_WIDTH,
            height=self.WINDOW_HEIGHT,
            bg="#24485B",
        )

        self.panel.pack(
            side=tk.RIGHT,
            fill=tk.Y,
            expand=False,
        )

        self.panel.pack_propagate(False)

        # Set the combined window size.
        self.root.update_idletasks()
        self.root.geometry(
            f"{self.MAP_WIDTH + self.PANEL_WIDTH}"
            f"x{self.WINDOW_HEIGHT}"
        )
        self.root.resizable(False, False)

        # Remove Salabim's window-wide pan and zoom handlers.
        for sequence in (
            "<ButtonPress-1>",
            "<B1-Motion>",
            "<ButtonRelease-1>",
            "<MouseWheel>",
            "<TouchpadScroll>",
        ):
            self.root.unbind(sequence)

        # Handle panning only on the map canvas.
        self.canvas.bind(
            "<ButtonPress-1>",
            self.start_map_pan,
        )

        self.canvas.bind(
            "<B1-Motion>",
            self.do_map_pan,
        )

        self.canvas.bind(
            "<ButtonRelease-1>",
            self.end_map_pan,
        )

        # Mouse-wheel zoom.
        if sys.platform.startswith("linux"):

            self.canvas.bind(
                "<Button-4>",
                lambda event: self.zoom_at_center(True),
            )

            self.canvas.bind(
                "<Button-5>",
                lambda event: self.zoom_at_center(False),
            )

            self.canvas.bind(
                "<MouseWheel>",
                self.on_mousewheel,
            )

        else:

            self.canvas.bind(
                "<MouseWheel>",
                self.on_mousewheel,
            )


    def clamp_camera_origin(
        self,
        x0,
        y0,
        view_width,
        view_height,
    ):
        """Keep the island inside the map viewport."""

        map_left, map_bottom, map_right, map_top = self.map_bounds

        # Horizontal limits.
        min_x0 = min(
            map_left,
            map_right - view_width,
        )

        max_x0 = max(
            map_left,
            map_right - view_width,
        )

        # Vertical limits.
        min_y0 = min(
            map_bottom,
            map_top - view_height,
        )

        max_y0 = max(
            map_bottom,
            map_top - view_height,
        )

        x0 = max(min_x0, min(x0, max_x0))
        y0 = max(min_y0, min(y0, max_y0))

        return x0, y0


    def start_map_pan(self, event):
        """Remember the camera position when dragging starts."""

        env = self.env

        scale = env._scale

        if scale <= 0:
            scale = env._scalez

        self._pan_start = (
            event.x,
            event.y,
            env._x0z,
            env._y0z,
            env._x1z - env._x0z,
            env._y1z - env._y0z,
            scale,
        )

        self.canvas.configure(cursor="fleur")

        return "break"


    def do_map_pan(self, event):
        """Pan the map while respecting its boundaries."""

        if self._pan_start is None:
            return "break"

        env = self.env

        (
            start_x,
            start_y,
            start_x0,
            start_y0,
            view_width,
            view_height,
            scale,
        ) = self._pan_start

        # Convert mouse movement from pixels to world coordinates.
        dx = -(event.x - start_x) / scale
        dy = (event.y - start_y) / scale

        new_x0 = start_x0 + dx
        new_y0 = start_y0 + dy

        # Prevent the map from being dragged out of view.
        new_x0, new_y0 = self.clamp_camera_origin(
            new_x0,
            new_y0,
            view_width,
            view_height,
        )

        env._x0z = new_x0
        env._y0z = new_y0

        env._x1z = new_x0 + view_width
        env._y1z = new_y0 + view_height

        return "break"


    def end_map_pan(self, event):
        """Finish dragging the map."""

        self._pan_start = None

        self.canvas.configure(cursor="")

        return "break"


    def zoom_at_center(self, zoom_in):
        """Zoom around the centre of the map viewport."""

        env = self.env

        # Same zoom factor used by Salabim.
        if zoom_in:
            factor = 1 / env._zoom_factor
        else:
            factor = env._zoom_factor

        # Current visible world dimensions.
        view_width = env._x1z - env._x0z
        view_height = env._y1z - env._y0z

        # Keep the world coordinate at the viewport centre fixed.
        center_x = (env._x0z + env._x1z) / 2
        center_y = (env._y0z + env._y1z) / 2

        # Calculate new visible dimensions.
        new_width = view_width * factor
        new_height = view_height * factor

        # Update Salabim's zoom scale.
        env._scalez /= factor

        # Calculate the new camera origin.
        new_x0 = center_x - new_width / 2
        new_y0 = center_y - new_height / 2

        # Apply the island boundaries.
        new_x0, new_y0 = self.clamp_camera_origin(
            new_x0,
            new_y0,
            new_width,
            new_height,
        )

        env._x0z = new_x0
        env._y0z = new_y0

        env._x1z = new_x0 + new_width
        env._y1z = new_y0 + new_height

        return "break"


    def on_mousewheel(self, event):
        """Handle mouse-wheel zoom on Windows, macOS and Linux."""

        delta = getattr(event, "delta", 0)

        if delta == 0:
            return "break"

        # Normalise wheel movement into zoom steps.
        steps = int(abs(delta) / 120)

        # Handle touchpads that report smaller deltas.
        if steps == 0:
            steps = 1

        zoom_in = delta > 0

        for _ in range(steps):
            self.zoom_at_center(zoom_in)

        return "break"


    def build_widgets(self):
        """Construct the fixed dashboard interface."""

        content = tk.Frame(
            self.panel,
            bg="#24485B",
            padx=15,
            pady=12,
        )

        content.pack(fill=tk.BOTH, expand=True)

        # Main heading.
        tk.Label(
            content,
            text="ISLAND SURVIVORS",
            font=("Segoe UI", 18, "bold"),
            fg="#F4EBD0",
            bg="#24485B",
        ).pack(anchor="w", pady=(0, 8))

        self.add_divider(content)

        # --------------------------------------------------
        # TEAM OVERVIEW
        # --------------------------------------------------

        self.add_heading(content, "TEAM OVERVIEW")

        self.team_var = tk.StringVar()

        tk.Label(
            content,
            textvariable=self.team_var,
            font=("TkFixedFont", 9),
            fg="#FFFFFF",
            bg="#24485B",
            justify=tk.LEFT,
            anchor="nw",
            height=3,
        ).pack(anchor="w")

        # --------------------------------------------------
        # EXPLORER SELECTION
        # --------------------------------------------------

        self.add_heading(content, "SELECT EXPLORER")

        button_frame = tk.Frame(
            content,
            bg="#24485B",
        )

        button_frame.pack(fill=tk.X, pady=(2, 2))

        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

        for index, explorer in enumerate(self.explorers):

            button = tk.Button(
                button_frame,
                text=explorer.name,
                command=lambda name=explorer.name: (
                    self.select_explorer(name)
                ),
                bg=explorer.color,
                fg="#FFFFFF",
                activebackground=explorer.color,
                activeforeground="#FFFFFF",
                font=("Segoe UI", 9, "bold"),
                width=13,
                height=1,
                relief=tk.RAISED,
                bd=1,
                cursor="hand2",
            )

            button.grid(
                row=index // 2,
                column=index % 2,
                padx=5,
                pady=3,
                sticky="ew",
            )

            self.buttons[explorer.name] = button

        self.add_divider(content)

        # --------------------------------------------------
        # EXPLORER INSPECTOR
        # --------------------------------------------------

        self.add_heading(content, "EXPLORER INSPECTOR")

        self.inspector_var = tk.StringVar()

        tk.Label(
            content,
            textvariable=self.inspector_var,
            font=("TkFixedFont", 9),
            fg="#FFFFFF",
            bg="#24485B",
            justify=tk.LEFT,
            anchor="nw",
            height=7,
            wraplength=315,
        ).pack(anchor="w")

        self.add_divider(content)

        # --------------------------------------------------
        # TEAM STORAGE
        # --------------------------------------------------

        self.add_heading(content, "TEAM STORAGE")

        self.storage_var = tk.StringVar()

        tk.Label(
            content,
            textvariable=self.storage_var,
            font=("TkFixedFont", 9),
            fg="#FFFFFF",
            bg="#24485B",
            justify=tk.LEFT,
            anchor="nw",
        ).pack(anchor="w")

        self.add_divider(content)

        # --------------------------------------------------
        # SHARED KNOWLEDGE
        # --------------------------------------------------

        self.add_heading(content, "SHARED KNOWLEDGE")

        self.knowledge_summary_var = tk.StringVar()

        tk.Label(
            content,
            textvariable=self.knowledge_summary_var,
            font=("TkFixedFont", 8),
            fg="#FFFFFF",
            bg="#24485B",
            justify=tk.LEFT,
            anchor="w",
        ).pack(anchor="w", pady=(0, 3))

        # Scrollable list of known resources.
        knowledge_frame = tk.Frame(
            content,
            bg="#24485B",
        )

        knowledge_frame.pack(
            fill=tk.X,
            pady=(0, 2),
        )

        self.knowledge_list = tk.Listbox(
            knowledge_frame,
            height=4,
            font=("TkFixedFont", 8),
            fg="#FFFFFF",
            bg="#1B3948",
            selectbackground="#52798A",
            activestyle="none",
            relief=tk.FLAT,
            highlightthickness=0,
        )

        knowledge_scrollbar = tk.Scrollbar(
            knowledge_frame,
            orient=tk.VERTICAL,
            command=self.knowledge_list.yview,
        )

        self.knowledge_list.configure(
            yscrollcommand=knowledge_scrollbar.set,
        )

        self.knowledge_list.pack(
            side=tk.LEFT,
            fill=tk.BOTH,
            expand=True,
        )

        knowledge_scrollbar.pack(
            side=tk.RIGHT,
            fill=tk.Y,
        )

        self.add_divider(content)

        # --------------------------------------------------
        # RECENT EVENTS
        # --------------------------------------------------

        self.add_heading(content, "RECENT EVENTS")

        self.events_var = tk.StringVar()

        tk.Label(
            content,
            textvariable=self.events_var,
            font=("TkFixedFont", 9),
            fg="#FFFFFF",
            bg="#24485B",
            justify=tk.LEFT,
            anchor="nw",
            height=4,
            wraplength=315,
        ).pack(anchor="w")

    def add_heading(self, parent, text):
        """Add a dashboard section heading."""

        tk.Label(
            parent,
            text=text,
            font=("Segoe UI", 11, "bold"),
            fg="#E9C879",
            bg="#24485B",
        ).pack(anchor="w", pady=(7, 3))

    def add_divider(self, parent):
        """Add a subtle horizontal divider."""

        tk.Frame(
            parent,
            bg="#52798A",
            height=1,
        ).pack(fill=tk.X, pady=5)

    def select_explorer(self, explorer_name):
        """Select an explorer for inspection."""

        for explorer in self.explorers:
            if explorer.name == explorer_name:
                self.selected_explorer = explorer
                break

        self.update_view()

    def team_overview_text(self):
        """Build the current team overview."""

        explorer = self.selected_explorer

        if explorer is None:
            return "No explorer selected."

        team_id = explorer.team_id

        team_explorers = [
            member
            for member in self.explorers
            if member.team_id == team_id
        ]

        alive_count = sum(
            member.is_alive
            for member in team_explorers
        )

        knowledge = self.team_knowledge_boards.get(team_id)

        known_count = 0

        if knowledge is not None:
            known_count = sum(
                resource["quantity"] > 0
                for resource in knowledge.known_resources.values()
            )

        
        leader = self.team_leaders.get(team_id)

        if leader is not None:

            leader_status = (
                "ALIVE" if leader.is_alive else "DEAD"
            )

            leader_text = (
                f"Leader: {leader_status} | "
                f"HP: {leader.health} | "
                f"Hunger: {leader.hunger}"
            )

        else:
            leader_text = "Leader: unavailable"

        return (
            f"Team: {team_id} | Time: {self.env.now():.1f}\n"
            f"Alive: {alive_count}/{len(team_explorers)} | "
            f"Known sites: {known_count}\n"
            f"{leader_text}"
        )

    def selected_explorer_text(self):
        """Build the current selected-explorer information."""

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

        if len(reason_text) > 38:
            reason_text = reason_text[:35] + "..."

        return (
            f"{explorer.name} | {status} | Team {explorer.team_id}\n"
            f"Position: ({explorer.row}, {explorer.col})\n"
            f"Health: {explorer.health}/100\n"
            f"Hunger: {explorer.hunger}/100\n"
            f"Inventory: W:{inventory.get('wood', 0)} "
            f"S:{inventory.get('stone', 0)} "
            f"B:{inventory.get('berries', 0)}\n"
            f"Action: {action_text}\n"
            f"Reason: {reason_text}"
        )

    def get_last_decision(self, explorer_name):
        """Find the latest decision made by an explorer."""

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
        """Build the selected team's storage information."""

        explorer = self.selected_explorer

        if explorer is None:
            return "No team selected."

        storage = self.team_storages.get(explorer.team_id)

        if storage is None:
            return "Storage unavailable."

        inventory = storage.inventory

        return (
            f"Wood: {inventory.get('wood', 0)}  "
            f"Stone: {inventory.get('stone', 0)}  "
            f"Berries: {inventory.get('berries', 0)}"
        )


    def knowledge_panel_data(self):
        """Build the selected team's shared knowledge information."""

        explorer = self.selected_explorer

        if explorer is None:
            return "No team selected.", []

        team_id = explorer.team_id

        knowledge = self.team_knowledge_boards.get(team_id)

        if knowledge is None:
            return f"Team {team_id}: knowledge unavailable.", []

        # Get a snapshot through the public TeamKnowledge API.
        resources = knowledge.get_resources()

        # Sort resources by their map position.
        resources.sort(
            key=lambda resource: resource["position"]
        )

        if not resources:
            return (
                f"Team {team_id} | 0 known sites",
                ["No shared discoveries yet."],
            )

        rows = []

        for resource in resources:

            row, col = resource["position"]

            resource_type = (
                resource.get("resource_type")
                or resource.get("kind", "resource")
            )

            quantity = resource.get("quantity", 0)

            observer = resource.get(
                "last_observed_by",
                "?",
            )

            observed_at = resource.get(
                "last_observed_at",
            )

            time_text = ""

            if isinstance(observed_at, (int, float)):
                time_text = f"T{observed_at:.1f}"

            rows.append(
                f"{resource_type} ({row},{col}) "
                f"q={quantity} | {observer} {time_text}"
            )

        summary = (
            f"Team {team_id} | "
            f"{len(resources)} known resource sites"
        )

        return summary, rows
    

    def recent_events_text(self):
        """Build the latest meaningful team events."""

        explorer = self.selected_explorer

        if explorer is None:
            return "No events."

        events = self.event_logger.get_recent_events(
            limit=4,
            team_id=explorer.team_id,
            include_debug=False,
        )

        if not events:
            return "Waiting for events..."

        return "\n".join(
            f"T={event['time']:.0f} "
            f"{event['explorer']} {event['event']}"
            for event in reversed(events)
        )

    def update_view(self):
        """Update dashboard widgets without scheduling another refresh."""

        if self._closed:
            return

        try:
            self.team_var.set(self.team_overview_text())
            self.inspector_var.set(self.selected_explorer_text())
            self.storage_var.set(self.storage_text())
            self.events_var.set(self.recent_events_text())

            # Update shared knowledge.
            knowledge_summary, knowledge_rows = (
                self.knowledge_panel_data()
            )

            self.knowledge_summary_var.set(
                knowledge_summary
            )

            # Only redraw the list when its contents change.
            current_rows = self.knowledge_list.get(
                0,
                tk.END,
            )

            if current_rows != tuple(knowledge_rows):

                previous_scroll_position = (
                    self.knowledge_list.yview()[0]
                )

                self.knowledge_list.delete(
                    0,
                    tk.END,
                )

                for row in knowledge_rows:
                    self.knowledge_list.insert(
                        tk.END,
                        row,
                    )

                self.knowledge_list.yview_moveto(
                    previous_scroll_position
                )

            # Highlight the currently selected explorer.
            for name, button in self.buttons.items():

                if (
                    self.selected_explorer is not None
                    and name == self.selected_explorer.name
                ):
                    button.configure(relief=tk.SUNKEN, bd=2)

                else:
                    button.configure(relief=tk.RAISED, bd=1)

        except tk.TclError:
            self.stop_refresh()


    def start_refresh(self):
        """Start exactly one periodic refresh loop."""

        if self._closed or self._refresh_job is not None:
            return

        self._refresh_job = self.root.after(
            250,
            self._refresh_tick,
        )


    def _refresh_tick(self):
        """Perform one update and schedule the next one."""

        self._refresh_job = None

        if self._closed:
            return

        self.update_view()
        self.start_refresh()


    def stop_refresh(self):
        """Stop the periodic dashboard update."""

        self._closed = True

        if self._refresh_job is not None:

            try:
                self.root.after_cancel(self._refresh_job)

            except tk.TclError:
                pass

            self._refresh_job = None
