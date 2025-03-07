#!/bin/bash
set -e

# Configuration
VERSION="0.1.6"
GITHUB_USER="taylorwilsdon"
REPO="reclaimed"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Starting release process for reclaimed v${VERSION}${NC}"

# 1. Ensure we're on the main branch
git checkout main
# Skip git pull if no upstream is configured
git rev-parse --abbrev-ref @{upstream} >/dev/null 2>&1 && git pull || echo "No upstream branch configured, skipping pull"

# 2. Clean build artifacts
echo -e "${YELLOW}Cleaning previous build artifacts...${NC}"
rm -rf dist/ build/ *.egg-info/

# 3. Build the package with UV
echo -e "${YELLOW}Building package with UV...${NC}"
# Build with UV
uv build --no-build-isolation

# 4. Create and push git tag
echo -e "${YELLOW}Creating and pushing git tag v${VERSION}...${NC}"
# Check if tag already exists
if git rev-parse "v${VERSION}" >/dev/null 2>&1; then
  echo -e "${YELLOW}Tag v${VERSION} already exists, skipping tag creation${NC}"
else
  git tag -a "v${VERSION}" -m "Release v${VERSION}"
fi
# Push tag to remote
git push origin refs/tags/"v${VERSION}" || echo "Failed to push tag, continuing anyway"

# 5. Create GitHub release
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

# 6. Download the tarball to calculate SHA
echo -e "${YELLOW}Downloading tarball to calculate SHA...${NC}"
TARBALL_PATH="/tmp/${REPO}-${VERSION}.tar.gz"
if curl -sL --fail "https://github.com/${GITHUB_USER}/${REPO}/archive/refs/tags/v${VERSION}.tar.gz" -o "${TARBALL_PATH}"; then
  SHA=$(shasum -a 256 "${TARBALL_PATH}" | cut -d ' ' -f 1)
  
  # 7. Update Homebrew formula with the SHA
  if [ -n "$SHA" ]; then
    echo -e "${YELLOW}Updating Homebrew formula with SHA: ${SHA}${NC}"
    sed -i '' "s/REPLACE_WITH_ACTUAL_SHA/${SHA}/" homebrew/reclaimed.rb
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
    uv publish
fi

# 9. Update Homebrew formula with correct dependency URLs and SHAs
echo -e "${YELLOW}Updating Homebrew formula with correct dependency URLs and SHAs...${NC}"
DEPS=("click" "rich" "textual")
for dep in "${DEPS[@]}"; do
  # Get package info directly from PyPI JSON API
  echo -e "${YELLOW}Fetching info for ${dep}...${NC}"
  JSON_INFO=$(curl -s "https://pypi.org/pypi/${dep}/json")
  
  # Get latest version
  LATEST_VERSION=$(echo "$JSON_INFO" | grep -o '"version":"[^"]*"' | head -1 | cut -d'"' -f4)
  echo -e "${YELLOW}Latest version: ${LATEST_VERSION}${NC}"
  
  # Get sdist URL and SHA
  SDIST_URL=$(echo "$JSON_INFO" | grep -o '"url":"[^"]*\.tar\.gz[^"]*"' | head -1 | cut -d'"' -f4)
  SDIST_SHA=$(echo "$JSON_INFO" | grep -o "\"${SDIST_URL}\".*\"sha256\":\s*\"[^\"]*\"" | grep -o '"sha256":\s*"[^"]*"' | cut -d'"' -f4)
  
  if [ -n "$SDIST_URL" ] && [ -n "$SDIST_SHA" ]; then
    echo -e "${YELLOW}Updating ${dep} to ${SDIST_URL} with SHA ${SDIST_SHA}${NC}"
    # Update the formula - use different approach to avoid sed issues
    awk -v url="$SDIST_URL" -v sha="$SDIST_SHA" -v dep="$dep" '
      /resource "'$dep'"/ {p=1}
      p && /url / {sub(/url ".*"/, "url \""url"\""); p=0}
      p && /sha256 / {sub(/sha256 ".*"/, "sha256 \""sha"\""); p=0}
      {print}
    ' homebrew/reclaimed.rb > homebrew/reclaimed.rb.tmp
    mv homebrew/reclaimed.rb.tmp homebrew/reclaimed.rb
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
