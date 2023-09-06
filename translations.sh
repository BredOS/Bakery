#!/bin/bash

# Get the directory of the script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Function to display usage instructions
function usage {
    echo "Usage: $0 --lang <language> --country <country> --action <create-pot/create-po/update-po/compile-mo>"
    exit 1
}

# Initialize variables
LANGUAGE=""
COUNTRY=""
ACTION=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --lang)
            shift
            LANGUAGE=$1
            ;;
        --country)
            shift
            COUNTRY=$1
            ;;
        --action)
            shift
            ACTION=$1
            ;;
        *)
            echo "Error: Unknown argument $1"
            usage
            ;;
    esac
    shift
done

# Check if required arguments are provided
if [[ -z "$LANGUAGE" || -z "$COUNTRY" || -z "$ACTION" ]]; then
    echo "Error: Language, country, and action must be provided."
    usage
fi

LC_COUNTRY=$(echo "$COUNTRY" | tr '[:upper:]' '[:lower:]')

# Define paths relative to the script's directory
BASE_DIR="$SCRIPT_DIR/locale"
POT_FILE="$BASE_DIR/bakery.pot"
PO_DIR="$BASE_DIR/$LANGUAGE/LC_MESSAGES"
PO_FILE="$PO_DIR/bakery.po"
MO_FILE="$PO_DIR/bakery.mo"

# Perform the specified action
case "$ACTION" in
    create-pot)
        mkdir -p "$BASE_DIR"
        xgettext -L Python -o "$POT_FILE" "$SCRIPT_DIR"/*.py
        echo "POT file created: $POT_FILE"
        ;;
    create-po)
        mkdir -p "$PO_DIR"
        msginit --input="$POT_FILE" --locale="$LANGUAGE"_"$COUNTRY".UTF-8 --output="$PO_FILE"
        echo "PO file created: $PO_FILE"
        ;;
    update-po)
        xgettext -L Python -o "$POT_FILE" "$SCRIPT_DIR"/*.py
        msgmerge --update "$PO_FILE" "$POT_FILE"
        echo "PO file updated: $PO_FILE"
        ;;
    compile-mo)
        msgfmt -o "$MO_FILE" "$PO_FILE"
        echo "MO file compiled: $MO_FILE"
        ;;
    *)
        echo "Error: Invalid action. Supported actions are 'create-pot', 'create-po', 'update-po', and 'compile-mo'."
        usage
        ;;
esac

echo "Action '$ACTION' completed successfully."