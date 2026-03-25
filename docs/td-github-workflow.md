# TouchDesigner to GitHub Workflow Guide

A reusable checklist for packaging and publishing TouchDesigner projects on GitHub.

## Repo Structure

```
project-name/
├── README.md
├── LICENSE
├── .gitignore
├── .gitattributes
├── ProjectName.toe
├── src/
│   ├── glsl/          # externalized shaders
│   └── scripts/       # externalized Python DATs
└── tox/
    └── ComponentName.tox
```

- `src/` contains all externalized human-readable files (GLSL, Python, JSON, CSV, etc.)
- `tox/` contains reusable components exported from the project
- The `.toe` sits at the root — it's the runnable project file
- Only add folders you actually need. No empty placeholder directories.

## Step-by-Step Workflow

### 1. Create the repo on GitHub

- Use lowercase with hyphens for the repo name (e.g. `particle-system-td`)
- Check "Add a README file" and select a license (MIT is a safe default)
- Clone it locally: `git clone <url>`

### 2. Create `.gitignore`

```
# TouchDesigner
Backup/
CrashAutoSave.*
*.toe.dir/
log.txt

# Numbered backup toe files (e.g. project.1234.toe)
*.*.toe

# Media (too large for git)
*.mp4
*.mov
*.wav
*.avi

# OS
.DS_Store
Thumbs.db
```

### 3. Create `.gitattributes`

```
*.toe binary
*.tox binary
```

If using Git LFS for large binaries:

```
*.toe filter=lfs diff=lfs merge=lfs -text
*.tox filter=lfs diff=lfs merge=lfs -text
```

### 4. Set up the folder structure

```bash
mkdir src
mkdir src/glsl    # or src/scripts, as needed
mkdir tox
```

### 5. Prepare the TouchDesigner project

#### Externalize files

Any Text DAT, GLSL DAT, or Table DAT can point to an external file instead of storing content inside the `.toe`. Do this for all shaders and Python scripts.

- In the parameter panel, set the "File" parameter to a **relative** path like `src/glsl/main.glsl`
- Relative paths are critical — absolute paths break when the project moves to another machine

#### Set up external `.tox` references

For each major component you want to be reusable:

1. Right-click the COMP → "Save Component .tox..." → save to `tox/ComponentName.tox`
2. On the COMP's **Common** page, set the **External .tox** parameter to point to `tox/ComponentName.tox`
3. **Turn OFF "Save Backup of External"** — otherwise TD saves a copy inside the `.toe`, bloating the file
4. Save the `.tox` again (so the external path is stored inside it)
5. Save the `.toe` last

After this setup, you mostly save individual `.tox` files during development, not the `.toe`.

#### Clean the network before committing

- Remove test/debug nodes, unused nodes, and dead connections
- Align and organize the node layout so it's readable
- Add network comments or colored network boxes to label sections
- Set window/resolution to sensible defaults (e.g. 1920x1080)

#### Rename the `.toe` cleanly

Drop date prefixes or working-copy names. Use the project name directly: `ParticleSystem.toe`, not `251209_ParticleSystem_v3_final.toe`. Git tracks the history for you.

### 6. Test before committing

Open the `.toe` and verify:

- All external file paths resolve correctly
- All `.tox` references load properly
- The project runs without errors

### 7. Stage and commit

```bash
git status                    # review what will be tracked
git add .gitignore .gitattributes
git add README.md LICENSE
git add src/
git add tox/
git add ProjectName.toe
git status                    # double check before committing
git commit -m "initial project setup with externalized source and tox components"
git push
```

Stage files explicitly rather than `git add -A` to avoid accidentally committing large or unwanted files.

## Ongoing Workflow

```bash
# after making changes in TouchDesigner, save your tox/glsl/scripts, then:
git status
git add src/glsl/modified_shader.glsl
git add tox/UpdatedComponent.tox
git commit -m "describe what changed and why"
git push
```

- **Commit `src/` files freely** — Git handles text diffs efficiently
- **Commit `.tox` and `.toe` files only at meaningful milestones** — each commit stores a full binary copy
- **Commit the `.toe` only when** you add/remove components at the project level, change project settings, or change perform window config

## Tips

- **Branching for experiments**: `git checkout -b experiment/new-particle-behaviour` lets you try things without affecting your main branch. Merge back with `git merge` if it works out.
- **Tags for releases**: `git tag v1.0` marks a version. Push tags with `git push --tags`. Use GitHub Releases to attach a description and preview media.
- **Preview media**: Keep a short GIF or screenshot in the repo for the README. A `preview.gif` at root or in a `docs/` folder works well. Keep it under 5MB.
- **Git LFS**: Consider it if your `.toe` exceeds ~50MB. Install with `git lfs install`, then track files with `git lfs track "*.toe"`.
- **Don't store video/audio assets in git.** Use a shared drive, cloud storage, or document the asset requirements in the README so others can source their own.
