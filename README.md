# Title

<!-- ![Preview](preview.gif) -->

## How It Works

## Parameters

| Page | Parameter | Description |
|-------|-----------|-------------|
| **Page** | `Parameter Name` | Description of Parameter |

## Project Structure

```
├── Project.toe             # Full runnable project
├── src/
│   └── glsl/
│       ├── x.glsl       
│       └── y.glsl             
│   └── scripts/ 
│       ├── a.py          
│       └── b.py            
|       
└── tox/
    └── Project.tox         # Importable component
```

## Requirements

- TouchDesigner 2023.11760 (or later)
- GPU with OpenGL 4.3+ support

## Usage

### Open full project

Open `Project.toe` in TouchDesigner.

### Import as component

Drag `tox/Project.tox` into any TouchDesigner project to use the particle system as a standalone module. Need to move the `src` files accordingly.

## License

MIT