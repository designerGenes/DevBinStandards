#!/usr/bin/env zsh

# extract_copilot_instructions.sh
# Finds all copilot-instructions.md files and copies them to a central library
# with descriptive names based on their project path

set -euo pipefail

# Configuration
INSTRUCTIONS_REPO="$HOME/DEV/.github/copilot-instructions-repo"
CACHE_FILE="$INSTRUCTIONS_REPO/.file_cache"
SEARCH_DIR="${1:-.}"
FORCE_REFRESH="${2:-}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Create the instructions repository
mkdir -p "$INSTRUCTIONS_REPO"

echo "${BLUE}=== Copilot Instructions Extractor ===${NC}"
echo "Searching in: $SEARCH_DIR"
echo "Output directory: $INSTRUCTIONS_REPO"
echo ""

# Find all copilot-instructions.md files (with caching)
if [[ "$FORCE_REFRESH" == "--refresh" || ! -f "$CACHE_FILE" ]]; then
    echo "${YELLOW}Finding copilot-instructions.md files...${NC}"
    find "$SEARCH_DIR" -type f -name "copilot-instructions.md" 2>/dev/null > "$CACHE_FILE"
    echo "${GREEN}Cache updated${NC}"
else
    echo "${YELLOW}Using cached file list (use --refresh to update)${NC}"
fi

# Read files from cache
files=()
while IFS= read -r file; do
    [[ -n "$file" ]] && files+=("$file")
done < "$CACHE_FILE"

if [[ ${#files[@]} -eq 0 ]]; then
    echo "${RED}No copilot-instructions.md files found.${NC}"
    exit 1
fi

echo "${GREEN}Found ${#files[@]} files${NC}"
echo ""

# Process each file
for file in "${files[@]}"; do
    # Skip empty files
    if [[ ! -s "$file" ]]; then
        echo "${YELLOW}Skipping (empty): $file${NC}"
        continue
    fi
    
    # Extract project path components for a meaningful name
    # Example: /Users/.../DEV/01_active_projects/33ter/backend/.github/copilot-instructions.md
    # Should become: 33ter-backend.md
    
    # Get the path relative to DEV
    rel_path="${file#*DEV/}"
    
    # Remove .github/copilot-instructions.md
    rel_path="${rel_path%/.github/copilot-instructions.md}"
    
    # Take the last 2-3 meaningful directory components
    # Convert path separators to dashes and clean up
    filename=$(echo "$rel_path" | tr '/' '-' | sed 's/^[0-9]*_//' | sed 's/-[0-9]*_/-/g')
    
    # Clean up the filename
    filename=$(echo "$filename" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9-]/-/g' | sed 's/--*/-/g' | sed 's/^-//' | sed 's/-$//')
    
    # Add .md extension
    filename="${filename}.md"
    
    output_path="$INSTRUCTIONS_REPO/$filename"
    
    # Check if this exact content already exists
    if [[ -f "$output_path" ]]; then
        if diff -q "$file" "$output_path" >/dev/null 2>&1; then
            echo "${YELLOW}⊘ Duplicate: $filename${NC}"
            continue
        else
            # If different content, append a number
            base="${filename%.md}"
            counter=2
            while [[ -f "$INSTRUCTIONS_REPO/${base}-${counter}.md" ]]; do
                ((counter++))
            done
            filename="${base}-${counter}.md"
            output_path="$INSTRUCTIONS_REPO/$filename"
        fi
    fi
    
    # Copy the file
    cp "$file" "$output_path"
    
    echo "${GREEN}✓ Copied: $filename${NC}"
    echo "  Source: $file"
done

echo ""
echo "${GREEN}✓ Complete!${NC}"
echo "Instructions saved to: $INSTRUCTIONS_REPO"
echo ""
echo "Total files processed: ${#files[@]}"
echo "Instructions available: $(find "$INSTRUCTIONS_REPO" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')"
