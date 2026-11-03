# cq_mod3d

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![CadQuery](https://img.shields.io/badge/CadQuery->=2.3.0-green.svg)](https://github.com/CadQuery/cadquery)

**cq_mod3d** is a powerful extension library built for [CadQuery](https://github.com/CadQuery/cadquery). It greatly simplifies 3D geometry translation, scaling, rotation, twisting, and shearing through elegant operator overloading. It also features a procedural noise generator based on mesh deformation and pure B-rep slice-and-loft algorithms, allowing you to easily transform regular engineering models into natural shapes like rocks, tree trunks, and mountains.

## ✨ Core Features

- **🚀 Seamless Operator Overloading**: Directly use `+`, `-`, `*`, `@`, `%`, and `^` on `cq.Workplane` objects for boolean operations, translation, scaling, rotation, shearing, and twisting.
- **🪨 Procedural Natural Textures (Noise)**: With just one line of code, you can apply uneven rock/bark textures to regular models. The library automatically repairs mesh seams to ensure the resulting solid is watertight.
- **🌀 Pure B-rep Twist**: Provides a slice-and-loft algorithm to generate perfect B-rep twisted bodies when applicable, with a seamless fallback to mesh twisting if it fails.
- **📐 Rich 2D/3D Primitives**: Includes dozens of unconventional geometric shapes such as Archimedean spirals, astroids, cardioids, hyperbolas, cycloids, and more.
- **🛠️ CQ-Editor Friendly**: Fully compatible with CQ-Editor. All 3D functions return native `Workplane` objects.

---

## 📦 Installation

You can install the latest version directly from GitHub:

```bash
pip install git+https://github.com/gwangcode/cq_mod3d.git
```

If you are developing locally, you can clone the source code and perform an editable install:

```bash
git clone https://github.com/gwangcode/cq_mod3d.git
cd cq_mod3d
pip install -e .
```

🚀 Quick Start
In your CQ-Editor or any Python script, just import cq_mod3d once, and all operator patches will be automatically activated.

```python
import cq_mod3d as m3
```

# 1. Quickly generate primitives using built-in functions
```python
base = m3.cube(10)
```

# 2. Use it like native CadQuery, but with superpowers!
## Translation: + [x, y, z]
```python
shifted = base + [15, 0, 0]
```

## Scaling: * number (uniform) / * [a, b, c] (non-uniform)
```python
scaled = base * [2, 1, 0.5]
```

## Boolean Intersection: * Workplane
```python
intersected = base * m3.sphere(6)
```

## Rotation: @ [rx, ry, rz] (radians)
```python
rotated = base @ [0, 0, 1.57]
```

## Shear: % [sxy, sxz, syx, syz, szx, szy]
sheared = base % [0.5, 0, 0, 0, 0, 0]

## Display
```python
show_object(shifted, name="Shifted", options={"color": (1, 0, 0)})
show_object(scaled, name="Scaled", options={"color": (0, 1, 0)})
```

# 🪨 Procedural Natural Textures (Noise)
cq_mod3d provides an algorithm based on normal displacement and 3D Gaussian noise, which can transform highly regular models (like spheres, cylinders, boxes) into natural, irregular shapes.

## Basic Usage
```python
import cq_mod3d as m3
```

## Generate a rock (deformed from a sphere)
```python
rock = m3.sphere(5)
rough_rock = m3.apply_noise(rock, density=0.8, smoothness=1.5, amplitude=0.5)
```

## Generate a tree trunk with rough bark (deformed from a cylinder)
```python
wood = m3.cylinder(radius=2, height=20)
rough_wood = m3.apply_noise(wood, density=0.2, smoothness=3.0, amplitude=0.3)

show_object(rough_rock, name="Rock")
```

| Parameter | Meaning | Recommended (Rock) | Recommended (Wood/Mountain) |
| :--- | :--- | :--- | :--- |
| **density** | **Noise density.** Larger values mean finer, more fragmented details; smaller values mean broader undulations. | `0.8 ~ 1.5` | `0.05 ~ 0.2` |
| **smoothness** | **Smoothness.** Larger values yield smoother surfaces; smaller values yield sharper, more rugged surfaces. | `1.0 ~ 2.0` | `3.0 ~ 5.0` |
| **amplitude** | **Amplitude.** The depth of displacement between the highest peaks and lowest valleys. | `0.1 ~ 0.3` | `0.2 ~ 0.5` |

⚠️ Note: To ensure the final model is watertight, cq_mod3d internally uses the ShapeFix tool to forcibly repair seams. If the noise amplitude is too large and causes severe mesh self-intersections, it will fall back to a Shell and print a warning. For 3D printing, it is recommended to keep amplitude under 20% of the model's minimum dimension.

# 🌀 Pure B-rep Twist
CadQuery natively does not support twisting complex solids. cq_mod3d provides the brep_twist_z function, which generates perfect solids via a "slice-rotate-loft" method with zero watertightness issues.

```python
import cq_mod3d as m3


part = m3.cuboid(5, 5, 20)
# Twist 180 degrees along the Z-axis (sections=50 for a smooth surface)
twisted = m3.brep_twist_z(part, angle_deg=180, sections=50)

# Or use the ^ operator directly (the system will automatically choose B-rep or mesh twist)
twisted_op = part ^ [0, 0, 3.14]
```
# 📐 Operator Overloading Cheatsheet
As long as you import cq_mod3d, all cq.Workplane objects gain the following capabilities:


| Operator | Operand | Equivalent Action | Example |
| :--- | :--- | :--- | :--- |
| `+` | `Workplane` | Boolean Union | `cube(2) + sphere(1)` |
| `+` | `[x, y, z]` | Translate | `cube(2) + [10, 0, 0]` |
| `-` | `Workplane` | Boolean Difference (Cut) | `cube(2) - sphere(1)` |
| `-` | `[x, y, z]` | Translate (Inverse) | `cube(2) - [10, 0, 0]` |
| `*` | `Workplane` | Boolean Intersection | `cube(2) * sphere(1.5)` |
| `*` | `int / float` | Uniform Scale | `cube(2) * 3` |
| `*` | `[a, b, c]` | Non-uniform Scale | `cube(2) * [2, 1, 0.5]` |
| `@` | `[rx, ry, rz]` | Rotate (radians) | `cube(2) @ [0, 0, 1.57]` |
| `%` | `[6 factors]` | Shear | `cube(2) % [0.5, 0, 0, 0, 0, 0]` |
| `^` | `[ax, ay, az]` | Twist | `cylinder(1, 10) ^ [0, 0, 1]` |

# 🎨 Built-in Primitive Library
## 3D Primitives
In addition to the natively supported cuboid, sphere, cylinder, cone, and torus, we also provide:

**Polyhedra:** tetrahedron, octahedron, dodecahedron, icosahedron

**Derived Shapes:** ellipsoid, prism, pyramid, convex_hull

## 2D Profile Curves (Returns Shape2d objects)
Includes a rich set of mathematical curve generators, easily usable for extrude or sweep operations:
*polygon, circle, ellipse, parabola, hyperbola, spiral, cardioid, cycloid, astroid, catenary, epicycloid, hypocycloid, lemniscate, semicircle, sine, tangent*.

All 2D objects support similar +, -, *, @ operations for booleans and transforms, and can be converted to a sketch anytime via .to_workplane().

# 🛠️ Dependencies
* [CadQuery](#) (>=2.3.0)
* [NumPy](#)
* [SciPy](#) (For 3D noise Gaussian filtering)
* [Trimesh](#) (For mesh normal calculation and deformation)
* [Shapely](#) (For 2D boolean operations)


# 📄 License
This project is licensed under the MIT License.
