#!/bin/bash
set -e

# Configuration - Version comes from version.py
VERSION_FILE="reclaimed/version.py"
GITHUB_USER="taylorwilsdon"
REPO="reclaimed"
UPDATE_DEPS_ONLY=false

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --update-deps-only) UPDATE_DEPS_ONLY=true ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Extract version from version.py file
VERSION=$(grep -o '__version__ = "[^"]*"' "$VERSION_FILE" | cut -d'"' -f2)
echo -e "${YELLOW}Starting release process for reclaimed v${VERSION}${NC}"

# 1. Check for required tools
if ! command -v jq &> /dev/null; then
  echo -e "${YELLOW}jq not found. Please install it to update dependencies.${NC}"
  echo -e "${YELLOW}On macOS: brew install jq${NC}"
  exit 1
fi

if [ "$UPDATE_DEPS_ONLY" = false ]; then
    # 2. Ensure we're on the main branch
    git checkout main
    # Skip git pull if no upstream is configured
    git rev-parse --abbrev-ref @{upstream} >/dev/null 2>&1 && git pull || echo "No upstream branch configured, skipping pull"

    # 3. Clean build artifacts
    echo -e "${YELLOW}Cleaning previous build artifacts...${NC}"
    rm -rf dist/ build/ *.egg-info/

    # 4. Build the package with UV (both sdist and wheel)
    echo -e "${YELLOW}Building package with UV...${NC}"
    uv build --sdist --wheel || {
        echo -e "${YELLOW}Failed to build package${NC}"
        exit 1
    }

    # 5. Create and push git tag
    echo -e "${YELLOW}Creating and pushing git tag v${VERSION}...${NC}"
    # Improved tag handling - check both local and remote tags
    LOCAL_TAG_EXISTS=$(git tag -l "v${VERSION}")
    REMOTE_TAG_EXISTS=$(git ls-remote --tags origin "refs/tags/v${VERSION}" | wc -l)

    if [ -n "$LOCAL_TAG_EXISTS" ]; then
      echo -e "${YELLOW}Local tag v${VERSION} already exists${NC}"
    else
      git tag -a "v${VERSION}" -m "Release v${VERSION}"
      echo -e "${YELLOW}Created local tag v${VERSION}${NC}"
    fi
    
    # Only push if tag doesn't exist on remote
    if [ "$REMOTE_TAG_EXISTS" -eq 0 ]; then
      echo -e "${YELLOW}Pushing tag to remote...${NC}"
      git push origin "v${VERSION}" || echo "Failed to push tag, continuing anyway"
    else
      echo -e "${YELLOW}Remote tag v${VERSION} already exists, skipping push${NC}"
    fi

    # 6. Create GitHub release
    echo -e "${YELLOW}Creating GitHub release...${NC}"
    # Check if gh command is available
    if ! command -v gh &> /dev/null; then
      echo -e "${YELLOW}GitHub CLI not found. Please install it to create releases.${NC}"
      echo -e "${YELLOW}Skipping GitHub release creation.${NC}"
    else
      # Check if release already exists
      if gh release view "v${VERSION}" &>/dev/null; then
        echo -e "${YELLOW}Release v${VERSION} already exists, skipping creation${NC}"
      else
        gh release create "v${VERSION}" \
          --title "reclaimed v${VERSION}" \
          --notes "Release v${VERSION}" \
          ./dist/*
      fi
    fi

    # 7. Download the tarball to calculate SHA
    echo -e "${YELLOW}Downloading tarball to calculate SHA...${NC}"
    TARBALL_PATH="/tmp/${REPO}-${VERSION}.tar.gz"
    if curl -sL --fail "https://github.com/${GITHUB_USER}/${REPO}/archive/refs/tags/v${VERSION}.tar.gz" -o "${TARBALL_PATH}"; then
      SHA=$(shasum -a 256 "${TARBALL_PATH}" | cut -d ' ' -f 1)
      
      # Update Homebrew formula with the SHA
      if [ -n "$SHA" ]; then
        echo -e "${YELLOW}Updating Homebrew formula with new version, URL and SHA...${NC}"
        # Update version in the formula
        sed -i '' "s/version \".*\"/version \"${VERSION}\"/" homebrew/reclaimed.rb
        # Update URL in the formula
        ESCAPED_URL=$(echo "https://github.com/${GITHUB_USER}/${REPO}/archive/refs/tags/v${VERSION}.tar.gz" | sed 's/[\/&]/\\&/g')
        sed -i '' "s|url \".*\"|url \"${ESCAPED_URL}\"|" homebrew/reclaimed.rb
        # Update SHA in the formula
        sed -i '' "s/sha256 \".*\"/sha256 \"${SHA}\"/" homebrew/reclaimed.rb
      else
        echo -e "${YELLOW}Failed to calculate SHA, skipping Homebrew formula update${NC}"
      fi
    else
      echo -e "${YELLOW}Failed to download tarball, skipping SHA calculation and Homebrew formula update${NC}"
    fi

    # 8. Publish to PyPI if desired
    read -p "Do you want to publish to PyPI? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]
    then
        echo -e "${YELLOW}Publishing to PyPI...${NC}"
        if ! uv publish; then
            echo -e "${YELLOW}Failed to publish to PyPI${NC}"
            exit 1
        fi
    fi
fi

# 9. Update Homebrew formula with correct dependency URLs and SHAs
echo -e "${YELLOW}Updating Homebrew formula with correct dependency URLs and SHAs...${NC}"

# Extract direct dependencies from pyproject.toml
echo -e "${YELLOW}Extracting direct dependencies from pyproject.toml...${NC}"
# More precisely extract only the dependencies section by using awk to get content between dependencies = [ and ]
DEPS_JSON=$(awk '/dependencies = \[/,/\]/' pyproject.toml | grep -v "dependencies = \[" | grep -v "\]" | sed 's/^[ \t]*//' | sed 's/,$//' | sed 's/"//g')
DIRECT_DEPS=()

# Parse the direct dependencies
while IFS= read -r line; do
    # Skip empty lines
    if [ -z "$line" ]; then
        continue
    fi
    # Extract package name (everything before >=, >, ==, or end of line)
    pkg=$(echo "$line" | sed -E 's/([^><=]+).*/\1/' | xargs)
    # Only add if not empty
    if [ -n "$pkg" ]; then
        DIRECT_DEPS+=("$pkg")
    fi
done <<< "$DEPS_JSON"

echo -e "${YELLOW}Found direct dependencies: ${DIRECT_DEPS[*]}${NC}"

# Create a temporary virtual environment to resolve all dependencies
echo -e "${YELLOW}Creating temporary virtual environment to resolve all dependencies...${NC}"
TEMP_VENV="/tmp/reclaimed_temp_venv"
python -m venv "$TEMP_VENV"
source "$TEMP_VENV/bin/activate"

# Install direct dependencies to resolve transitive dependencies
echo -e "${YELLOW}Installing dependencies to resolve full dependency tree...${NC}"
for dep in "${DIRECT_DEPS[@]}"; do
    pip install "$dep" >/dev/null 2>&1
done

# Get all installed packages (excluding standard library and development packages)
echo -e "${YELLOW}Extracting full dependency tree...${NC}"
ALL_DEPS=$(pip freeze | grep -v "^-e" | cut -d= -f1 | tr '[:upper:]' '[:lower:]')

# Create an array of all dependencies, normalizing names and avoiding duplicates
DEPS=()

while IFS= read -r pkg; do
    # Skip empty lines and the package itself
    if [ -z "$pkg" ] || [ "$pkg" = "reclaimed" ]; then
        continue
    fi
    
    # Normalize package name (use hyphens consistently)
    normalized_pkg=$(echo "$pkg" | tr '_' '-')
    
    # Check if this package is already in DEPS (avoid duplicates)
    is_duplicate=0
    for existing_dep in "${DEPS[@]}"; do
        if [ "$existing_dep" = "$normalized_pkg" ]; then
            is_duplicate=1
            break
        fi
    done
    
    # Only add if not a duplicate
    if [ "$is_duplicate" -eq 0 ]; then
        DEPS+=("$normalized_pkg")
    fi
done <<< "$ALL_DEPS"

# Clean up the temporary virtual environment
deactivate
rm -rf "$TEMP_VENV"

echo -e "${YELLOW}Found all dependencies: ${DEPS[*]}${NC}"

for dep in "${DEPS[@]}"; do
  echo -e "${YELLOW}Fetching info for ${dep}...${NC}"
  
  # Get package info from PyPI JSON API
  JSON_INFO=$(curl -s "https://pypi.org/pypi/${dep}/json")
  
  # Use jq to reliably extract information
  LATEST_VERSION=$(echo "$JSON_INFO" | jq -r '.info.version')
  echo -e "${YELLOW}Latest version: ${LATEST_VERSION}${NC}"
  
  # Get the sdist (tar.gz) URL and SHA
  SDIST_INFO=$(echo "$JSON_INFO" | jq -r '.urls[] | select(.packagetype=="sdist")')
  SDIST_URL=$(echo "$SDIST_INFO" | jq -r '.url')
  SDIST_SHA=$(echo "$SDIST_INFO" | jq -r '.digests.sha256')
  
  if [ -n "$SDIST_URL" ] && [ -n "$SDIST_SHA" ] && [ "$SDIST_URL" != "null" ] && [ "$SDIST_SHA" != "null" ]; then
    echo -e "${YELLOW}Updating ${dep} to ${SDIST_URL} with SHA ${SDIST_SHA}${NC}"
    
    # Escape URL and SHA for sed
    ESCAPED_URL=$(echo "$SDIST_URL" | sed 's/[\/&]/\\&/g')
    ESCAPED_SHA=$(echo "$SDIST_SHA" | sed 's/[\/&]/\\&/g')
    
    # Check if resource block exists for this dependency (checking both hyphen and underscore versions)
    hyphen_version=$(echo "$dep" | tr '_' '-')
    underscore_version=$(echo "$dep" | tr '-' '_')
    
    if grep -q "resource \"$hyphen_version\" do" homebrew/reclaimed.rb; then
      # Update existing resource block with hyphen version
      sed -i '' "/resource \"$hyphen_version\" do/,/end/ {
        s|url \".*\"|url \"$ESCAPED_URL\"|
        s|sha256 \".*\"|sha256 \"$ESCAPED_SHA\"|
      }" homebrew/reclaimed.rb
    elif grep -q "resource \"$underscore_version\" do" homebrew/reclaimed.rb; then
      # Update existing resource block with underscore version
      sed -i '' "/resource \"$underscore_version\" do/,/end/ {
        s|url \".*\"|url \"$ESCAPED_URL\"|
        s|sha256 \".*\"|sha256 \"$ESCAPED_SHA\"|
      }" homebrew/reclaimed.rb
    else
      # Add new resource block before the install method
      echo -e "${YELLOW}Adding new resource block for ${dep}${NC}"
      
      # Use awk to insert the new resource block before the install method
      # This is more reliable on macOS than sed for multi-line insertions
      awk -v url="$SDIST_URL" -v sha="$SDIST_SHA" -v dep="$dep" '
      /def install/ {
        print "  resource \"" dep "\" do";
        print "    url \"" url "\"";
        print "    sha256 \"" sha "\"";
        print "  end";
        print "";
        print $0;
        next;
      }
      { print }
      ' homebrew/reclaimed.rb > homebrew/reclaimed.rb.tmp
      
      mv homebrew/reclaimed.rb.tmp homebrew/reclaimed.rb
    fi
  else
    echo -e "${YELLOW}Failed to get URL and SHA for ${dep}${NC}"
  fi
done

# 10. Instructions for Homebrew tap
echo -e "${GREEN}Release v${VERSION} completed!${NC}"
echo -e "${GREEN}To publish to Homebrew:${NC}"
echo -e "1. Create a tap repository: github.com/${GITHUB_USER}/homebrew-tap"
echo -e "2. Copy homebrew/reclaimed.rb to your tap repository"
echo -e "3. Users can then install with: brew install ${GITHUB_USER}/tap/reclaimed"

echo -e "${GREEN}Done!${NC}"
