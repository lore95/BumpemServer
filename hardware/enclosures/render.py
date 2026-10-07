"""Offscreen VTK render of a CadQuery part to PNG (shaded + feature edges), used by overview.py."""
import tempfile
from pathlib import Path

import cadquery as cq
import vtk


def _actors(wp, color, opacity):
    with tempfile.TemporaryDirectory() as d:
        stl = Path(d) / "p.stl"
        cq.exporters.export(wp, str(stl), tolerance=0.02, angularTolerance=0.1)
        reader = vtk.vtkSTLReader(); reader.SetFileName(str(stl)); reader.Update()
    normals = vtk.vtkPolyDataNormals(); normals.SetInputConnection(reader.GetOutputPort()); normals.SetFeatureAngle(30); normals.SplittingOn()
    mapper = vtk.vtkPolyDataMapper(); mapper.SetInputConnection(normals.GetOutputPort())
    actor = vtk.vtkActor(); actor.SetMapper(mapper)
    pr = actor.GetProperty(); pr.SetColor(*color); pr.SetSpecular(0.25); pr.SetSpecularPower(20); pr.SetDiffuse(0.8); pr.SetAmbient(0.25)
    edges = vtk.vtkFeatureEdges(); edges.SetInputConnection(reader.GetOutputPort()); edges.SetFeatureAngle(30)
    edges.BoundaryEdgesOn(); edges.FeatureEdgesOn(); edges.ManifoldEdgesOff(); edges.NonManifoldEdgesOff()
    em = vtk.vtkPolyDataMapper(); em.SetInputConnection(edges.GetOutputPort()); em.ScalarVisibilityOff()
    ea = vtk.vtkActor(); ea.SetMapper(em); ea.GetProperty().SetColor(0.15, 0.17, 0.2); ea.GetProperty().SetLineWidth(1.5)
    pr.SetOpacity(opacity); ea.GetProperty().SetOpacity(min(1.0, opacity + 0.2))
    return actor, ea


def render_png(items, path: Path, size=(1400, 1000)) -> None:
    """items: list of (workplane, rgb, opacity); the first is the printed part."""
    ren = vtk.vtkRenderer(); ren.SetBackground(1, 1, 1)
    for wp, color, opacity in items:
        for a in _actors(wp, color, opacity):
            ren.AddActor(a)
    win = vtk.vtkRenderWindow(); win.SetOffScreenRendering(1); win.AddRenderer(ren); win.SetSize(*size)
    cam = ren.GetActiveCamera(); cam.SetPosition(1, -1.3, 0.9); cam.SetFocalPoint(0, 0, 0); cam.SetViewUp(0, 0, 1)
    ren.ResetCamera(); cam.Zoom(1.25)
    win.Render()
    w2i = vtk.vtkWindowToImageFilter(); w2i.SetInput(win); w2i.Update()
    png = vtk.vtkPNGWriter(); png.SetFileName(str(path)); png.SetInputConnection(w2i.GetOutputPort()); png.Write()
