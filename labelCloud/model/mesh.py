import ctypes
import logging
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import numpy.typing as npt
import OpenGL.GL as GL
from ..io.pointclouds import BasePointCloudHandler, Open3DHandler
SIZE_OF_FLOAT = ctypes.sizeof(ctypes.c_float)


class Mesh:
    def __init__(
        self,
        path: Path,
        vertices: npt.NDArray[np.float32],
        triangles: npt.NDArray[np.uint32],
        colors: Optional[npt.NDArray[np.float32]] = None,
        normals: Optional[npt.NDArray[np.float32]] = None,
    ) -> None:
        self.path = path
        self.vertices = vertices
        self.triangles = triangles
        self.colors = colors if isinstance(colors, np.ndarray) and len(colors) > 0 else None
        self.normals = normals if isinstance(normals, np.ndarray) and len(normals) > 0 else None
        
        self.vertex_vbo: Optional[int] = None
        self.normal_vbo: Optional[int] = None
        self.color_vbo: Optional[int] = None
        self.ibo: Optional[int] = None
        self.brightness: float = 0.5

        logging.info(f"Loaded mesh from {path.name}: "
                     f"{len(vertices)} vertices, {len(triangles)} triangles.")

    def create_buffers(self) -> None:
        """Upload vertex, color and index data to the GPU. Must be called inside an active GL context."""
        #self.vertex_vbo, self.color_vbo, self.ibo = GL.glGenBuffers(3)
        self.vertex_vbo = GL.glGenBuffers(1)
        self.normal_vbo  = GL.glGenBuffers(1)
        self.color_vbo  = GL.glGenBuffers(1)
        self.ibo        = GL.glGenBuffers(1)
        # Vertex positions
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vertex_vbo)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, self.vertices.nbytes,
                        self.vertices, GL.GL_STATIC_DRAW)

        # Vertex colors (fallback to grey if absent)
        color_data = self.colors if self.colors is not None else (
            np.full_like(self.vertices, 0.75, dtype=np.float32)
        )
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.color_vbo)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, color_data.nbytes,
                        color_data, GL.GL_STATIC_DRAW)

        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

        # Normals
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.normal_vbo)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, self.normals.nbytes,
                        self.normals, GL.GL_STATIC_DRAW)

        # Triangle indices
        indices = self.triangles.flatten().astype(np.uint32)
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, self.ibo)
        GL.glBufferData(GL.GL_ELEMENT_ARRAY_BUFFER, indices.nbytes,
                        indices, GL.GL_STATIC_DRAW)
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, 0)


    def compute_vertex_normals(self):
        normals = np.zeros_like(self.points)

        for tri in self.faces:
            v0, v1, v2 = self.points[tri]
            n = np.cross(v1 - v0, v2 - v0)
            normals[tri] += n

        norms = np.linalg.norm(normals, axis=1, keepdims=True)
        normals /= np.maximum(norms, 1e-8)

        self.normals = normals.astype(np.float32)

    def draw(self, alpha: float = 0.6) -> None:
        if self.vertex_vbo is None:
            logging.warning("draw() called before create_buffers() — skipping mesh draw.")
            return

        # No transform call here — paintGL's outer matrix scope already has
        # set_gl_background() applied via draw_pointcloud()

        stride = 3 * SIZE_OF_FLOAT
        n_indices = self.triangles.size

        GL.glEnable(GL.GL_LIGHTING)

        # Near-zero global ambient so unlit faces are dark, maximising surface contrast
        GL.glLightModelfv(GL.GL_LIGHT_MODEL_AMBIENT, [0.05, 0.05, 0.05, 1.0])

        b = self.brightness
        # Key light: strong, from upper-front-right
        GL.glEnable(GL.GL_LIGHT0)
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_POSITION, [1.0, 1.0, 2.0, 0.0])
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_AMBIENT,  [b * 0.3, b * 0.3, b * 0.3, 1.0])
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_DIFFUSE,  [1.0, 1.0, 1.0, 1.0])
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_SPECULAR, [0.2, 0.2, 0.2, 1.0])

        # Fill light: dimmer, from lower-back-left; softens pure-black shadows
        # without flattening the overall shading contrast
        GL.glEnable(GL.GL_LIGHT1)
        GL.glLightfv(GL.GL_LIGHT1, GL.GL_POSITION, [-1.0, -1.0, -0.5, 0.0])
        GL.glLightfv(GL.GL_LIGHT1, GL.GL_AMBIENT,  [0.0, 0.0, 0.0, 1.0])
        GL.glLightfv(GL.GL_LIGHT1, GL.GL_DIFFUSE,  [0.35, 0.35, 0.35, 1.0])
        GL.glLightfv(GL.GL_LIGHT1, GL.GL_SPECULAR, [0.0, 0.0, 0.0, 1.0])

        GL.glEnable(GL.GL_COLOR_MATERIAL)
        GL.glColorMaterial(GL.GL_FRONT_AND_BACK, GL.GL_AMBIENT_AND_DIFFUSE)

        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vertex_vbo)
        GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
        GL.glVertexPointer(3, GL.GL_FLOAT, stride, None)

        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.normal_vbo)
        GL.glEnableClientState(GL.GL_NORMAL_ARRAY)
        GL.glNormalPointer(GL.GL_FLOAT, stride, None)

        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.color_vbo)
        GL.glEnableClientState(GL.GL_COLOR_ARRAY)
        GL.glColorPointer(3, GL.GL_FLOAT, stride, None)

        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, self.ibo)
        GL.glDrawElements(GL.GL_TRIANGLES, n_indices, GL.GL_UNSIGNED_INT, None)

        GL.glDisableClientState(GL.GL_VERTEX_ARRAY)
        GL.glDisableClientState(GL.GL_COLOR_ARRAY)
        GL.glDisableClientState(GL.GL_NORMAL_ARRAY)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, 0)
        GL.glDisable(GL.GL_LIGHT1)
        GL.glDisable(GL.GL_LIGHTING)
        GL.glDisable(GL.GL_COLOR_MATERIAL)

    @classmethod
    def from_file(cls, path: Path) -> Optional["Mesh"]:
        if path.suffix.lower() not in {".ply", ".obj", ".stl"}:
            return None

        handler = Open3DHandler()
        vertices, colors, triangles, normals = handler.read_triangle_mesh(path)

        if triangles is None:
            return None  # not a real mesh
        
        return cls(path, vertices, triangles, colors, normals)

    @property
    def has_buffers(self) -> bool:
        return self.vertex_vbo is not None