"""Shared styles for reclaimed"""

# Selenized Dark color scheme hex values
BG_0 = "#103c48"  # darkest background
BG_1 = "#184956"  # darker background
BG_2 = "#2d5b69"  # content highlights
DIM_0 = "#72898f"  # dimmed text
FG_0 = "#adbcbc"  # main text
FG_1 = "#cad8d9"  # emphasized text
YELLOW = "#ebc13d"  # bright yellow
ORANGE = "#fd9456"  # bright orange
RED = "#ff665c"  # bright red
MAGENTA = "#ff84cd"  # bright magenta
VIOLET = "#bd96fa"  # bright violet
BLUE = "#58a3ff"  # bright blue
CYAN = "#53d6c7"  # bright cyan
GREEN = "#84c747"  # bright green

# Backward compatibility with old Solarized variable names
BASE03 = BG_0  # darkest background
BASE02 = BG_1  # darker background
BASE01 = BG_2  # content highlights
BASE00 = DIM_0  # dimmed text
BASE0 = FG_0  # main text
BASE1 = FG_1  # emphasized text
BASE2 = FG_1  # light content (mapped to emphasized text in selenized)
BASE3 = FG_1  # lightest (mapped to emphasized text in selenized)

# Theme-aware styles for the Textual UI. Every color comes from the active
# Textual theme, so switching themes updates the complete interface.
TEXTUAL_CSS = """
Screen {
    background: $background;
    color: $foreground;
}

#app-header {
    height: 3;
    background: $surface;
    color: $foreground;
    border-bottom: heavy $primary;
}

#app-header HeaderIcon {
    width: 7;
    padding: 0 2;
    color: $text-primary;
    background: $primary-muted;
    text-style: bold;
    content-align: center middle;
    pointer: pointer;
}

#app-header HeaderIcon:hover {
    color: $text;
    background: $primary;
}

#app-header HeaderTitle {
    padding: 0 2;
    color: $foreground;
    content-align: left middle;
}

#app-header HeaderClock {
    width: 11;
    padding: 0 2;
    color: $text-primary;
    background: $panel;
    border-left: solid $border-blurred;
    text-style: bold;
}

Footer {
    height: 1;
    background: $footer-background;
    color: $footer-foreground;
}

#main-container {
    width: 100%;
    height: 1fr;
    padding: 0 1;
    overflow: hidden;
}

#path-bar {
    height: 1;
    background: $surface;
    padding: 0 1;
    content-align: left middle;
}

#scan-progress {
    width: 9;
    height: 1;
    margin: 0 1 0 0;
    color: $primary;
    background: transparent;
}

#scan-state {
    width: 11;
    height: 1;
    margin: 0 1 0 0;
    content-align: center middle;
    text-style: bold;
}

#scan-state.scanning {
    color: $text-warning;
    background: $warning-muted;
}

#scan-state.paused {
    color: $text-accent;
    background: $accent-muted;
}

#scan-state.complete {
    color: $text-success;
    background: $success-muted;
}

#scan-state.failed {
    color: $text-error;
    background: $error-muted;
}

#path-display {
    width: 1fr;
    height: 1;
    color: $foreground-muted;
    text-overflow: ellipsis;
}

#summary-strip {
    height: 3;
    margin-top: 1;
    background: $surface;
}

.metric-card {
    width: 1fr;
    height: 3;
    padding: 0 1;
    border-right: solid $border-blurred;
}

.metric-card:last-child {
    border-right: none;
}

.metric-value {
    height: 1;
    color: $text-primary;
    text-style: bold;
}

.metric-label {
    height: 1;
    color: $foreground-muted;
    text-style: bold;
}

#scan-progress-bar {
    height: 1;
    margin: 0 1;
}

#toolbar {
    height: 3;
    margin-top: 1;
    align-vertical: middle;
}

/* Every toolbar child is three rows tall, so the labels, the sort control and
   the buttons all put their text on the same row. */
#results-title,
#sort-label {
    height: 3;
    content-align-vertical: middle;
}

#results-title {
    width: 1fr;
    margin-right: 2;
    text-wrap: nowrap;
    text-overflow: ellipsis;
    color: $foreground;
    text-style: bold;
}

#sort-label {
    width: auto;
    margin-right: 1;
    color: $foreground-muted;
}

#sort-select {
    width: 32;
    height: 3;
    margin-right: 1;
    /* Matches the flat buttons' block border so the picker sits in their row. */
    border: block $surface;
}

/* A compact Select drops its focus border, so mark focus the way Textual's own
   widgets do: tint the surface, no ring. */
#sort-select:focus {
    background-tint: $foreground 8%;
}

#toolbar Button {
    width: auto;
    margin-left: 1;
    pointer: pointer;
}

#delete-button {
    min-width: 10;
}

#pause-button {
    /* Wide enough for both labels so the toolbar does not shift on toggle. */
    min-width: 10;
}

#tables-container {
    width: 100%;
    height: 1fr;
    layout: vertical;
}

.table-panel {
    width: 100%;
    height: 1fr;
    margin-bottom: 1;
    background: $surface;
    border: tall $border-blurred;
}

.table-panel:focus-within {
    border: tall $primary;
}

.section-header {
    height: 2;
    padding: 0 1;
    background: $panel;
    content-align: left middle;
}

.section-title {
    width: 1fr;
    color: $foreground;
    text-style: bold;
}

.result-count {
    width: auto;
    color: $foreground-muted;
}

DataTable {
    width: 100%;
    height: 1fr;
    color: $foreground;
    background: $surface;
    border: none;
    scrollbar-size: 1 1;
}

DataTable > .datatable--header {
    background: $panel;
    color: $foreground;
    text-style: bold;
}

DataTable > .datatable--even-row {
    background: $boost;
}

DataTable > .datatable--cursor {
    background: $primary-muted;
    color: $text-primary;
    text-style: bold;
}

Screen.-wide #tables-container {
    layout: horizontal;
}

Screen.-wide .table-panel {
    width: 1fr;
    height: 100%;
    margin: 0 1 0 0;
}

Screen.-wide .table-panel:last-child {
    margin-right: 0;
}

Screen.-narrow #results-title,
Screen.-narrow #sort-label,
Screen.-narrow #theme-button {
    display: none;
}

/* Keep the scan controls on screen; the theme still has a key and the palette. */
Screen.-compact #theme-button {
    display: none;
}

Screen.-narrow #sort-select {
    width: 1fr;
}

ConfirmationDialog,
SortOptions {
    align: center middle;
    background: $background 75%;
}

#dialog-container,
#sort-container {
    width: 70;
    max-width: 92%;
    height: auto;
    background: $surface;
    border: tall $primary;
    padding: 1 2;
}

.dialog-eyebrow {
    height: 1;
    color: $text-primary;
    text-style: bold;
}

#dialog-title,
#sort-title {
    width: 100%;
    height: 2;
    color: $foreground;
    text-style: bold;
}

#dialog-path {
    width: 100%;
    height: auto;
    max-height: 4;
    margin: 1 0;
    padding: 1;
    color: $text-error;
    background: $error-muted;
    text-wrap: wrap;
}

#dialog-size-info {
    height: 1;
    margin: 0 0 1 0;
    color: $text-success;
    text-style: bold;
}

.dialog-warning {
    height: auto;
    color: $text-warning;
}

#dialog-buttons,
#sort-buttons {
    width: 100%;
    height: 3;
    margin-top: 1;
    align-horizontal: right;
}

#dialog-buttons Button,
#sort-buttons Button {
    width: auto;
    margin-left: 1;
    pointer: pointer;
}

RadioSet {
    width: 100%;
    background: transparent;
}

RadioButton {
    background: transparent;
    color: $foreground;
    pointer: pointer;
}
"""
