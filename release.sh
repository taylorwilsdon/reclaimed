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
git pull

# 2. Clean build artifacts
echo -e "${YELLOW}Cleaning previous build artifacts...${NC}"
rm -rf dist/ build/ *.egg-info/

# 3. Build the package with UV
echo -e "${YELLOW}Building package with UV...${NC}"
uv build

# 4. Create and push git tag
echo -e "${YELLOW}Creating and pushing git tag v${VERSION}...${NC}"
git tag -a "v${VERSION}" -m "Release v${VERSION}"
git push origin "v${VERSION}"

# 5. Create GitHub release
echo -e "${YELLOW}Creating GitHub release...${NC}"
gh release create "v${VERSION}" \
  --title "reclaimed v${VERSION}" \
  --notes "Release v${VERSION}" \
  ./dist/*

# 6. Download the tarball to calculate SHA
echo -e "${YELLOW}Downloading tarball to calculate SHA...${NC}"
curl -sL "https://github.com/${GITHUB_USER}/${REPO}/archive/refs/tags/v${VERSION}.tar.gz" -o "/tmp/${REPO}-${VERSION}.tar.gz"
SHA=$(shasum -a 256 "/tmp/${REPO}-${VERSION}.tar.gz" | cut -d ' ' -f 1)

# 7. Update Homebrew formula with the SHA
echo -e "${YELLOW}Updating Homebrew formula with SHA: ${SHA}${NC}"
sed -i '' "s/REPLACE_WITH_ACTUAL_SHA/${SHA}/" homebrew/reclaimed.rb

# 8. Publish to PyPI if desired
read -p "Do you want to publish to PyPI? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo -e "${YELLOW}Publishing to PyPI...${NC}"
    uv publish
fi

# 9. Instructions for Homebrew tap
echo -e "${GREEN}Release v${VERSION} completed!${NC}"
echo -e "${GREEN}To publish to Homebrew:${NC}"
echo -e "1. Create a tap repository: github.com/${GITHUB_USER}/homebrew-tap"
echo -e "2. Copy homebrew/reclaimed.rb to your tap repository"
echo -e "3. Users can then install with: brew install ${GITHUB_USER}/tap/reclaimed"

echo -e "${GREEN}Done!${NC}"
