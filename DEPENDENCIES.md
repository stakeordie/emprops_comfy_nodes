# Dependencies Management

## Submodules

### ComfyUI-VideoHelperSuite

Location: `deps/ComfyUI-VideoHelperSuite`
Original Repo: https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite
Our Fork: https://github.com/stakeordie/ComfyUI-VideoHelperSuite

#### Updating Process

1. Update our fork with upstream changes:
```bash
cd deps/ComfyUI-VideoHelperSuite
git fetch upstream
git merge upstream/main
git push origin main
cd ../..
```

2. Update the submodule reference in our main repo:
```bash
git submodule update --remote
git add deps/ComfyUI-VideoHelperSuite
git commit -m "chore: Update VideoHelperSuite submodule"
git push origin master
```

#### Initial Setup (for new clones)

After cloning the repository:
```bash
git submodule init
git submodule update
```

#### Adding New Dependencies

When adding new dependencies as submodules:
1. Fork the repository to the stakeordie organization
2. Add as submodule:
   ```bash
   git submodule add https://github.com/stakeordie/REPO_NAME.git deps/REPO_NAME
   ```
3. Set up upstream:
   ```bash
   cd deps/REPO_NAME
   git remote add upstream https://github.com/ORIGINAL_OWNER/REPO_NAME.git
   cd ../..
   ```
