"""Shared styles for reclaimed"""

# Selenized Dark color scheme hex values
BG_0 = "#103c48"     # darkest background
BG_1 = "#184956"     # darker background
BG_2 = "#2d5b69"     # content highlights
DIM_0 = "#72898f"    # dimmed text
FG_0 = "#adbcbc"     # main text
FG_1 = "#cad8d9"     # emphasized text
YELLOW = "#ebc13d"   # bright yellow
ORANGE = "#fd9456"   # bright orange
RED = "#ff665c"      # bright red
MAGENTA = "#ff84cd"  # bright magenta
VIOLET = "#bd96fa"   # bright violet
BLUE = "#58a3ff"     # bright blue
CYAN = "#53d6c7"     # bright cyan
GREEN = "#84c747"    # bright green

# Backward compatibility with old Solarized variable names
BASE03 = BG_0        # darkest background
BASE02 = BG_1        # darker background
BASE01 = BG_2        # content highlights
BASE00 = DIM_0       # dimmed text
BASE0 = FG_0         # main text
BASE1 = FG_1         # emphasized text
BASE2 = FG_1         # light content (mapped to emphasized text in selenized)
BASE3 = FG_1         # lightest (mapped to emphasized text in selenized)

# CSS styles for Textual UI
TEXTUAL_CSS = """
/* Define all variables at the start */
$bg_0: #103c48;      /* darkest background */
$bg_1: #184956;      /* darker background */
$bg_2: #2d5b69;      /* content highlights */
$dim_0: #72898f;     /* dimmed text */
$fg_0: #adbcbc;      /* main text */
$fg_1: #cad8d9;      /* emphasized text */
$yellow: #ebc13d;    /* bright yellow */
$orange: #fd9456;    /* bright orange */
$red: #ff665c;       /* bright red */
$magenta: #ff84cd;   /* bright magenta */
$violet: #bd96fa;    /* bright violet */
$blue: #58a3ff;      /* bright blue */
$cyan: #53d6c7;      /* bright cyan */
$green: #84c747;     /* bright green */


Screen {
    background: $bg_0;
    color: $fg_0;
}

#header {
    dock: top;
    height: 1;
    background: $bg_2;
    color: $fg_1;
    text-align: center;
    border-bottom: solid $fg_0;
}

#footer {
    height: 1;
    background: $bg_2;
    color: $fg_1;
    border-top: solid $fg_0;
}

#footer-container {
    dock: bottom;
    height: 2;
    align-horizontal: left;
}

#scan-progress {
    background: $bg_1;
}

Footer {
    height: 1;
}

#main-container {
    width: 100%;
    height: 100%;
    border-left: heavy $bg_2;
    border-right: heavy $bg_2;
}

#title {
    dock: top;
    height: 2;
    background: $bg_2;
    color: $fg_1;
    text-align: center;
    border-bottom: heavy $bg_1;
}

#status-bar {
    dock: top;
    height: 2;
    background: $bg_1;
    padding: 0 1;
    border-bottom: heavy $bg_2;
}

#status-label {
    width: auto;
    color: $fg_0;
}

#path-display {
    width: 1fr;
    color: $fg_0;
    padding: 0 1;
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
    padding-right: 1;
}
#files-section-header, #dirs-section-header {
    height: 1;
    background: $bg_1;
    padding-left: 1;
    color: $fg_1;
    margin-top: 1;
}

/* Remove dock: top to keep headers in normal flow */
#dirs-section-header {
    margin-top: 1;
}

#files-table, #dirs-table {
    width: 100%;
    color: $fg_0;
    background: $bg_0;
    border: heavy $fg_0;
}

#dirs-table {
    height: 45%;
    margin-bottom: 1;
}

#files-table {
    height: 50%;
}

DataTable {
    border: none;
}

DataTable > .datatable--header {
    background: $bg_1;
    color: $fg_1;
    border-bottom: heavy $bg_2;
}

DataTable > .datatable--cursor {
    background: $bg_2;
    color: $fg_1;
    border: round $bg_1;
}

#dialog-container {
    width: 100%;
    margin: 5;
    height: auto;
    background: $bg_1;
    border: tall $blue;
    padding: 1 2;
}

#dialog-title {
    width: 100%;
    height: 1;
    content-align: center middle;
    color: $fg_1;
}

#dialog-path {
    width: 100%;
    height: 2;
    content-align: center middle;
    margin: 1 0;
    color: $red;
}

#dialog-buttons {
    width: 100%;
    height: 3;
    content-align: center middle;
    margin-top: 1;
    align-horizontal: center;
}

#sort-container {
    width: 40%;
    height: auto;
    background: $bg_1;
    border: tall $blue;
    padding: 1 2;
}

#sort-title {
    width: 100%;
    height: 1;
    content-align: center middle;
    margin-bottom: 1;
    color: $fg_1;
}

#sort-buttons {
    width: 100%;
    height: 3;
    content-align: center middle;
    margin-top: 1;
}

Button {
    margin: 0 1;
    background: $bg_2;
    color: $fg_1;
}

Button:hover {
    background: $dim_0;
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
    background: $bg_1;
    color: $fg_1;
}

RadioButton.-selected {
    background: $blue;
    color: $fg_1;
}

"""
