# labelCloud

A tool for labeling 3D point clouds, with support for mesh overlays.

---

## Table of Contents

- [Features](#features)
- [Setup](#setup)
- [Folder Structure](#folder-structure)
- [Labeling](#labeling)
  - [Selecting Active Classes (Session Subset)](#selecting-active-classes-session-subset)
  - [Pick Point](#pick-point)
  - [Pick Flow](#pick-flow)
  - [Correcting a Placed Point](#correcting-a-placed-point)
  - [Label Output Format](#label-output-format)
  - [Bounding Box Modes](#bounding-box-modes)
- [Mesh Support](#mesh-support)
- [Import & Export Formats](#import--export-formats)
- [Configuration](#configuration)
- [Shortcuts](#shortcuts)

---

## Features

- **Pick Point:** Click to label a single point in the cloud and assign it a class
- **Pick Flow:** Rapidly label a sequence of classes in order — the tool auto-advances after each pick
- **Mesh overlay:** Display `.ply`, `.obj`, or `.stl` meshes alongside point clouds
- **Multiple export formats:** centroid, vertices, KITTI, and more
- **Label propagation:** Auto-copy labels to the next point cloud
- **Class management:** Configurable class names and colors

---

## Setup


### from source

```bash
git clone https://github.com/ch-sa/labelCloud.git
cd labelCloud
pip install -r requirements.txt
python3 labelCloud.py
```

On first launch a startup dialog will ask you to configure the labeling mode, class names, and export format. These settings are saved to `labels/_classes.json` and can be changed at any time via **Labels → Edit Classes**.

---

## Folder Structure

labelCloud expects point clouds in one folder and writes labels to another. Both paths are configurable (see [Configuration](#configuration)); the defaults are:

```
project/
├── pointclouds/      # Input point clouds (and optionally meshes)
├── labels/           # Output label JSON files
│   └── _classes.json # Class definitions (auto-created on first run)
├── calib/            # Calibration files (required for KITTI export only)
└── config.ini        # Project settings (auto-created on first run)
```

---

## Labeling

The two primary labeling modes are **Pick Point** and **Pick Flow**. Both work by snapping to the nearest actual point in the cloud when you click, so labels are always anchored to real geometry.

The label list on the right panel shows all placed labels for the current point cloud. Points are shown with a circle icon; bounding boxes (if any) with a cube icon. The active item is highlighted green in the 3D view.

---

### Selecting Active Classes (Session Subset)

On startup, a dialog shows your full class list with a **Select** checkbox next to each class. Only the classes you check here will be available during the session — they are the only classes that appear in the class dropdown and the only ones Pick Flow cycles through.

This is useful when your `_classes.json` defines a large set of landmarks or categories but you only need to annotate a subset for a given batch of point clouds.

**How it works:**

1. The startup dialog lists all classes with a **Select** checkbox per row. A **Select all** checkbox at the top controls the whole list at once.
2. Uncheck any classes you don't want to use. The remaining checked classes become the active set.
3. Click **Continue**. The selection is saved back to `labels/_classes.json` as a `"session"` flag on each class entry:

```json
{
    "classes": [
        {"name": "left_hip",  "id": 1, "color": "#ffbf35", "session": true},
        {"name": "right_hip", "id": 2, "color": "#35aaff", "session": true},
        {"name": "tail_base", "id": 3, "color": "#ff6b6b", "session": false}
    ]
}
```

4. During labeling, the class dropdown is populated only from classes where `session` is `true`. Pick Flow cycles through exactly that same filtered list.
5. The selection persists to the next session — on next launch the checkboxes are pre-filled from the saved `session` flags. Re-open the startup dialog via **Labels → Edit Classes** to change the active set at any time.

---

### Pick Point

Use this mode to place a single labeled point. Activate it with the **Pick Point** button in the toolbar.

**Workflow:**

1. Move your cursor over the point cloud. A yellow preview sphere snaps to the nearest point in real time.
2. When the preview is on the point you want, press **Ctrl+Click** to place it.
3. The point is added to the label list with the class currently selected in the class dropdown.
4. To change the class of the placed point, select it in the label list and change the dropdown.
5. Use `W` `A` `S` `D` / `Q` `E` to nudge the point's position if needed.
6. Click **Pick Point** again or press `Esc` to exit the mode.

**Behind the scenes:** When the strategy activates it builds a KDTree from the point cloud. Every mouse move queries the KDTree to find the nearest point and renders the preview. On Ctrl+Click the nearest point index and its 3D coordinates are recorded and stored in the label file.

---

### Pick Flow

Pick Flow is designed for scenes where you need to label the same ordered set of classes across many point clouds — for example, marking a fixed set of anatomical landmarks or sensor targets. The tool cycles through your class list automatically so you never have to touch the dropdown.

Activate it with the **Pick Flow** button in the toolbar.

**Workflow:**

1. The class dropdown shows the first class to place. A status label below it shows what comes next.
2. Move your cursor over the cloud — you get the same yellow preview snap as Pick Point.
3. Press **Ctrl+Click** to place the point for the current class.
4. The tool immediately advances to the next class. The dropdown and status label update.
5. Repeat for each class. When the last class is placed the cycle resets to the first class.
6. Press **Ctrl+Z** to undo the last placed point. The class index steps back so you can re-pick it.
7. If a class has no corresponding point in this cloud (e.g. it is occluded), use **Skip** to advance without placing.
8. Press `Esc` or click **Pick Flow** again to exit the mode.

**Tip:** The order classes appear in `labels/_classes.json` is the order Pick Flow cycles through them. Arrange your classes in the order you want to pick them.

---

### Correcting a Placed Point

After placing a point (in either mode), select it in the label list to make it active. Then:

| Key | Action |
| --- | ------ |
| `W` / `S` | Move forward / backward |
| `A` / `D` | Move left / right |
| `Q` / `E` | Move up / down |
| `Del` | Delete the point |
| Class dropdown | Reassign to a different class |

---

### Label Output Format

Each time you save, the tool writes **two files** for every point cloud: a standard label file and a MPI-format file. Both are written to the `labels/` folder.

---

#### Standard file — loaded by labelCloud

Filename: `<pointcloud_name>.json`

Points and bounding boxes are stored together in the `"objects"` array. A labeled point entry looks like this:

```json
{
    "folder": "pointclouds",
    "filename": "scan_001.ply",
    "path": "/path/to/pointclouds/scan_001.ply",
    "annotator": "your_name",
    "objects": [
        {
            "name": "left_hip",
            "point": [0.42318156, -1.08740234, 0.91200000],
            "point_idx": 4504
        },
        {
            "name": "right_hip",
            "point": [0.42318156, 1.08740234, 0.91200000],
            "point_idx": 9816
        }
    ]
}
```

- `"point"` — 3D coordinates as a flat `[x, y, z]` array
- `"point_idx"` — index of the picked point in the original point cloud array

This is the file labelCloud reads back when you re-open a session.

---

#### MPI file — for downstream processing

Filename: `<pointcloud_name>mpi_horse_ext.json`

Written automatically alongside the standard file. Uses a different structure with a flat `"keypoints"` array where each entry uses the class name as its key:

```json
{
    "metadata": {
        "folder": "pointclouds",
        "filename": "scan_001.ply",
        "path": "/path/to/pointclouds/scan_001.ply",
        "annotator": "your_name"
    },
    "keypoints": [
        {
            "left_hip": [0.42318156, -1.08740234, 0.91200000],
            "PCD_point_index": 4504
        },
        {
            "right_hip": [0.42318156, 1.08740234, 0.91200000],
            "PCD_point_index": 9816
        }
    ]
}
```

This file is not loaded by labelCloud — it exists for internal MPI pipeline use. Bounding box labels are skipped in this file; only picked points are written.

---

### Bounding Box Modes

labelCloud also supports 3D bounding box annotation (the original purpose of the tool). These modes are less central to typical point-picking workflows but are available if needed.

**Picking Mode** — click to place a box at a location, scroll to rotate it.

**Spanning Mode** — click four vertices in sequence to define the box: length endpoint, width endpoint, then height.

**Correction** — use the left panel buttons or keyboard shortcuts to adjust translation (`W` `A` `S` `D` / `Q` `E`), rotation (`Z`/`X`, `C`/`V`, `B`/`N`), and dimensions (`I`/`O`, `K`/`L`, `,`/`.`). Hover the cursor over a box face and scroll to resize that dimension (side-pulling).

By default only z-axis rotation is allowed. Enable full 3-axis rotation via **Settings → z-Rotation Only Mode**.

---

## Mesh Support

If a mesh file with the same base filename as the current point cloud is found in the point cloud folder, it is loaded and displayed as a semi-transparent overlay on top of the point cloud.

**Supported mesh formats:** `.ply`, `.obj`, `.stl`

Example — if your point cloud is `pointclouds/scan_001.pcd`, place a mesh at `pointclouds/scan_001.ply` (or `.obj` / `.stl`) and it will load automatically.

The mesh is rendered with:
- Per-vertex RGB colors (grey if none are present)
- Diffuse and ambient lighting using computed vertex normals
- Transparency (opacity ~0.6) so underlying points remain visible

---

## Import & Export Formats

### Supported Point Cloud Formats

| Type      | Extensions                              |
| --------- | --------------------------------------- |
| Colored   | `.pcd`, `.ply`, `.pts`, `.xyzrgb`       |
| Colorless | `.xyz`, `.xyzn`, `.bin` (KITTI)         |

Colorless point clouds are automatically colorized by height for easier navigation.

### Supported Label Export Formats

| Format                | Description                                                                                                   |
| --------------------- | ------------------------------------------------------------------------------------------------------------- |
| `centroid_rel`        | Centroid `[x, y, z]`; Dimensions `[length, width, height]`; Rotations as Euler angles in radians (−π…+π)    |
| `centroid_abs`        | Centroid `[x, y, z]`; Dimensions `[length, width, height]`; Rotations as Euler angles in degrees (0…360°)   |
| `vertices`            | 8 vertices of the bounding box, each as `[x, y, z]`                                                          |
| `kitti`               | KITTI-standard format with calibration file support                                                           |
| `kitti_untransformed` | KITTI structure without coordinate transformation                                                             |

---

## Configuration

Settings are stored in `config.ini` in your project directory. A default file is created on first run. You can also edit a subset of settings through the **Settings** menu in the GUI.

### Key Options

**[FILE]**

| Option               | Default                   | Description                                    |
| -------------------- | ------------------------- | ---------------------------------------------- |
| `pointcloud_folder`  | `pointclouds/`            | Folder to load point clouds from               |
| `label_folder`       | `labels/`                 | Folder to write label files to                 |
| `class_definitions`  | `labels/_classes.json`    | Class names, colors, and export format         |
| `calib_folder`       | `calib/`                  | Calibration files (KITTI export only)          |

**[POINTCLOUD]**

| Option                | Default        | Description                                         |
| --------------------- | -------------- | ---------------------------------------------------- |
| `point_size`          | `4.0`          | Rendered point diameter                              |
| `colorless_colorize`  | `True`         | Auto-colorize unlabeled clouds by height             |
| `colorless_color`     | `0.9, 0.9, 0.9`| Base color for unlabeled points                     |

**[LABEL]**

| Option                | Default | Description                                          |
| --------------------- | ------- | ---------------------------------------------------- |
| `std_translation`     | `0.03`  | Point movement step (meters)                         |
| `propagate_labels`    | `False` | Copy labels from previous point cloud if none exist  |

**[USER_INTERFACE]**

| Option              | Default        | Description                                               |
| ------------------- | -------------- | ---------------------------------------------------------- |
| `show_floor`        | `True`         | Display x-y grid                                          |
| `background_color`  | `100, 100, 100`| Viewer background RGB                                     |
| `keep_perspective`  | `False`        | Keep camera position when moving between point clouds     |

### Class Configuration (`labels/_classes.json`)

This file defines the classes available in the tool and the order Pick Flow cycles through them.

```json
{
    "classes": [
        {"name": "unassigned", "id": 0, "color": "#9da2ab"},
        {"name": "left_hip",   "id": 1, "color": "#ffbf35"},
        {"name": "right_hip",  "id": 2, "color": "#35aaff"}
    ],
    "default": 0,
    "type": "object_detection",
    "format": "centroid_abs"
}
```

Edit this file directly or use **Labels → Edit Classes** in the GUI. Changes take effect on the next app start.

---

## Shortcuts

| Shortcut | Action |
| :------: | ------ |
| **Camera** | |
| Left Mouse Button | Rotate camera around point cloud center |
| Right Mouse Button | Translate (pan) camera |
| Mouse Wheel | Zoom |
| `P` / `Home` | Reset camera perspective |
| **Point Picking** | |
| `Ctrl` + Left Click | Place point at cursor (snaps to nearest cloud point) |
| `Ctrl+Z` | Undo last placed point (also steps back class in Pick Flow) |
| `Esc` | Exit current labeling mode |
| **Point Correction** | |
| `W` `A` `S` `D` | Move point forward / left / back / right |
| `Q` `E` | Move point up / down |
| `Del` | Delete active point or bounding box |
| **Navigation** | |
| `R` / `Left` | Previous point cloud |
| `F` / `Right` | Next point cloud |
| `T` / `Up` | Previous label |
| `G` / `Down` | Next label |
| `Y` `H` | Cycle class backward / forward |
| `1`–`9` | Select label by index |
