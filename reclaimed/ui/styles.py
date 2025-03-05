"""Shared styles for reclaimed"""

# Solarized Dark color scheme hex values
BASE03 = "#002b36"
BASE02 = "#073642"
BASE01 = "#586e75"
BASE00 = "#657b83"
BASE0 = "#839496"
BASE1 = "#93a1a1"
BASE2 = "#eee8d5"
BASE3 = "#fdf6e3"
YELLOW = "#b58900"
ORANGE = "#cb4b16"
RED = "#dc322f"
MAGENTA = "#d33682"
VIOLET = "#6c71c4"
BLUE = "#268bd2"
CYAN = "#2aa198"
GREEN = "#859900"

# CSS styles for Textual UI
TEXTUAL_CSS = """
/* Define all variables at the start */
$base03: #002b36;
$base02: #073642;
$base01: #586e75;
$base00: #657b83;
$base0: #839496;
$base1: #93a1a1;
$base2: #eee8d5;
$base3: #fdf6e3;
$yellow: #b58900;
$orange: #cb4b16;
$red: #dc322f;
$magenta: #d33682;
$violet: #6c71c4;
$blue: #268bd2;
$cyan: #2aa198;
$green: #859900;


Screen {
    background: $base03;
    color: $base0;
}

#header {
    dock: top;
    height: 1;
    background: $base02;
    color: $base1;
    text-align: center;
}

#footer {
    dock: bottom;
    height: 1;
    background: $base02;
    color: $base1;
}

#main-container {
    width: 100%;
    height: 100%;
}

#title {
    dock: top;
    height: 1;
    background: $base02;
    color: $blue;
    text-align: center;
}

#status-bar {
    dock: top;
    height: 1;
    background: $base02;
    padding: 0 1;
}

#status-label {
    width: auto;
    color: $base01;
}

#path-display {
    width: 1fr;
    color: $base1;
}

#scan-timer {
    width: auto;
    color: $cyan;
    text-align: right;
    padding-right: 2;
}

#scan-count {
    width: auto;
    color: $blue;
    text-align: right;
}

#files-section-header, #dirs-section-header {
    height: 1;
    background: $base02;
    color: $blue;
    padding: 0 1;
    margin-top: 1;
}

/* Remove dock: top to keep headers in normal flow */
#dirs-section-header {
    margin-top: 1;
}

#files-table, #dirs-table {
    width: 100%;
    background: $base03;
    color: $base0;
}

#dirs-table {
    height: 40%;
    margin-bottom: 1;
}

#files-table {
    height: 40%;
}

DataTable {
    border: none;
}

DataTable > .datatable--header {
    background: $base02;
    color: $base1;
}

DataTable > .datatable--cursor {
    background: $base01;
}

#dialog-container {
    width: 60%;
    height: auto;
    background: $base02;
    border: tall $blue;
    padding: 1 2;
}

#dialog-title {
    width: 100%;
    height: 1;
    content-align: center middle;
    color: $base1;
}

#dialog-path {
    width: 100%;
    height: 3;
    content-align: center middle;
    margin: 1 0;
    color: $red;
}

#dialog-buttons {
    width: 100%;
    height: 3;
    content-align: center middle;
    margin-top: 1;
}

#sort-container {
    width: 40%;
    height: auto;
    background: $base02;
    border: tall $blue;
    padding: 1 2;
}

#sort-title {
    width: 100%;
    height: 1;
    content-align: center middle;
    margin-bottom: 1;
    color: $base1;
}

#sort-buttons {
    width: 100%;
    height: 3;
    content-align: center middle;
    margin-top: 1;
}

Button {
    margin: 0 1;
    background: $base01;
    color: $base2;
}

Button:hover {
    background: $base00;
}

Button.primary {
    background: $blue;
}

Button.success {
    background: $green;
}

Button.error {
    background: $red;
}

RadioButton {
    background: $base02;
    color: $base1;
}

RadioButton.-selected {
    background: $blue;
    color: $base3;
}

#footer-container {
    layout: horizontal;
    dock: bottom;
    height: 3;
    align-horizontal: left;
    align-vertical: middle;
    padding: 0 1;
}

#scan-progress {
    margin-left: 2;
    height: 1;
    background: $base02;
}

Footer {
    height: 1;
}
"""
