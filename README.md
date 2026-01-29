# MADD XP CLI Tool

MADD XP (`mxp`) is a command-line interface tool designed to extract and analyze object hierarchies from Copado Data Templates. It recursively traverses Data Templates (parents and children), resolves Salesforce object labels, and exports the results to CSV or JSON formats.

## Prerequisites

Before using this tool, ensure you have the following installed and configured:

1.  **Python 3.x**: Ensure Python is installed on your system.
2.  **Salesforce CLI (`sf`)**: This tool relies on the Salesforce CLI for authentication.
    *   Install the Salesforce CLI: Instructions here.
    *   **Authenticate**: You must be logged into the target Salesforce org via the CLI before running `mxp`.

    ```bash
    # Authenticate via web login
    sf org login web --alias cpdXpress --instance-url https://test.salesforce.com
    ```

## Installation

To install the tool locally, navigate to the project root directory and run:

```bash
pip install .
```

Once installed, the command `mxp` will be available in your terminal.

## Capabilities & Usage

The `mxp` tool allows you to inspect Copado Data Templates by providing either their names or Salesforce Record IDs. It handles complex hierarchies and outputs a flattened list of objects involved.

### Basic Command Structure

```bash
mxp -u <ORG_ALIAS> [INPUT_FLAGS] [OUTPUT_FLAGS]
```

### 1. Input Methods

You must provide at least one template to process using either names or IDs.

**By Template Name (`-t`)**
```bash
# Single template
mxp -u cpdXpress -t "MADD Stress Main"

# Multiple templates
mxp -u cpdXpress -t "Template A" "Template B"

# JSON Array string
mxp -u cpdXpress -t '["Template A", "Template B"]'
```

**By Record ID (`-i`)**
```bash
# Single ID
mxp -u cpdXpress -i a0UQH000005LJXs2AO

# Multiple IDs
mxp -u cpdXpress -i a0UQH000005LJXs2AO a0UQH000005MrUD2A0
```

### 2. Output Formats

By default, the tool generates a CSV file named `objects_list.csv` in the current directory.

**Custom Output Path (`-o`)**
```bash
mxp -u cpdXpress -t "Template A" -o ./exports/my_analysis.csv
```

**JSON Output (`--json`)**
Instead of CSV, you can export the data as a JSON file.
```bash
mxp -u cpdXpress -t "Template A" --json
```

### 3. Help

To see the full list of options and examples directly in your terminal:

```bash
mxp --help
```

## Output Data

The generated output contains the following columns/fields:

*   **Input Template Name**: The root template requested by the user.
*   **Object Label**: The user-friendly label of the Salesforce object (e.g., "Account").
*   **Object API Name**: The API name (e.g., `Account`, `Custom_Object__c`).
*   **Template Name**: The specific template record name found in the hierarchy.
*   **Template Id**: The Salesforce ID of the template.
*   **Root Template**: Boolean indicating if this row represents the root template itself.