"""Overloads domain-specific methods onto topologic.CellComplex"""

import topologic
from topologic import FaceUtility, CellUtility
from topologist.helpers import el
import topologist.traces
import topologist.hulls
import topologist.normals


def AllocateCells(self, widgets):
    """Set cell types using widgets, or default to 'Outside'"""
    cells_ptr = []
    self.Cells(None, cells_ptr)
    for cell in cells_ptr:
        cell.Set("usage", "living")
        # a usable space has vertical faces on all sides
        if not cell.Perimeter(self).is_simple_cycle():
            cell.Set("usage", "void")
            continue
        for widget in widgets:
            if CellUtility.Contains(cell, widget[1], 0.001) == 0:
                cell.Set("usage", widget[0].lower())
                break


# TODO non-horizontal details (gables, arches, ridges and valleys)


def GetTraces(self):
    """Traces are 2D ugraph paths that define walls, extrusions and rooms"""
    mytraces = topologist.traces.Traces()
    myhulls = topologist.hulls.Hulls()
    mynormals = topologist.normals.Normals()
    elevations = {}
    faces_ptr = []
    self.Faces(None, faces_ptr)

    for face in faces_ptr:
        # labelling "badnormal" faces should be a separate method but here is convenient for now
        face.BadNormal(self)
    for face in faces_ptr:
        stylename = face.Get("stylename")
        cells_ordered = face.CellsOrdered(self)
        if not stylename:
            stylename = "default"
        if face.IsVertical():
            elevation = face.Elevation()
            height = face.Height()

            axis = face.AxisOuter()
            # wall face may be triangular and not have a bottom edge
            if axis:
                if face.IsOpen(self):
                    mytraces.add_axis(
                        "open", elevation, height, stylename, axis, face, cells_ordered
                    )

                elif face.IsExternal(self):
                    mytraces.add_axis(
                        "external",
                        elevation,
                        height,
                        stylename,
                        axis,
                        face,
                        cells_ordered,
                    )

                elif face.IsInternal(self):
                    mytraces.add_axis_simple(
                        "internal",
                        elevation,
                        height,
                        stylename,
                        axis,
                        face,
                        cells_ordered,
                    )

                    # collect foundation strips
                    if not face.FaceBelow(self):
                        mytraces.add_axis_simple(
                            "internal-unsupported",
                            elevation,
                            0.0,
                            stylename,
                            axis,
                            face,
                            cells_ordered,
                        )
                elevations[elevation] = 0
            else:
                # face has no horizontal bottom edge, add to hull for wall panels
                myhulls.add_face("panel", stylename, face, cells_ordered)

            # TODO open wall top and bottom traces
            if face.IsExternal(self):
                normal = face.Normal()
                for condition in face.TopLevelConditions(self):
                    edge = condition[0]
                    vertices = [edge.EndVertex(), edge.StartVertex()]
                    if face.Get("badnormal"):
                        vertices.reverse()
                    label = condition[1]
                    mytraces.add_axis(
                        label,
                        el(elevation + height),
                        0.0,
                        stylename,
                        vertices,
                        face,
                        cells_ordered,
                    )
                    mynormals.add_vector("top", edge.StartVertex(), normal)
                    mynormals.add_vector("top", edge.EndVertex(), normal)
                    elevations[el(elevation + height)] = 0

                for condition in face.BottomLevelConditions(self):
                    edge = condition[0]
                    vertices = [edge.StartVertex(), edge.EndVertex()]
                    if face.Get("badnormal"):
                        vertices.reverse()
                    label = condition[1]
                    mytraces.add_axis(
                        label,
                        elevation,
                        0.0,
                        stylename,
                        vertices,
                        face,
                        cells_ordered,
                    )
                    mynormals.add_vector("bottom", edge.StartVertex(), normal)
                    mynormals.add_vector("bottom", edge.EndVertex(), normal)

        elif face.IsHorizontal():
            # collect flat roof areas (not outdoor spaces)
            if face.IsUpward() and face.IsWorld(self):
                myhulls.add_face("flat", stylename, face, cells_ordered)
        else:
            # collect roof, soffit, and vaulted ceiling faces as hulls
            if face.IsUpward():
                myhulls.add_face("roof", stylename, face, cells_ordered)
            else:
                myhulls.add_face("soffit", stylename, face, cells_ordered)

    cells_ptr = []
    self.Cells(None, cells_ptr)
    for cell in cells_ptr:
        perimeter = cell.Perimeter(self)
        if perimeter.is_simple_cycle():
            elevation = cell.Elevation()
            height = cell.Height()
            faces_bottom = []
            cell.FacesBottom(faces_bottom)
            stylename = faces_bottom[0].Get("stylename")
            if not stylename:
                stylename = "default"

            usage = cell.Usage()
            mytraces.add_trace(usage, elevation, height, stylename, perimeter)
            elevations[elevation] = 0

    mytraces.process()
    myhulls.process()
    mynormals.process()
    level = 0
    keys = list(elevations.keys())
    keys.sort()
    for elevation in keys:
        elevations[elevation] = level
        level += 1
    return (mytraces.traces, myhulls.hulls, mynormals.normals, elevations)


def ApplyDictionary(self, source_faces_ptr):
    """Copy Dictionary items from a collection of faces"""
    faces_ptr = []
    self.Faces(None, faces_ptr)
    for face in faces_ptr:
        vertex = FaceUtility.InternalVertex(face, 0.001)
        for source_face in source_faces_ptr:
            if FaceUtility.IsInside(source_face, vertex, 0.001):
                dictionary = source_face.GetDictionary()
                for key in dictionary.Keys():
                    face.Set(key, source_face.Get(key).split(".")[0])
                break


setattr(topologic.CellComplex, "AllocateCells", AllocateCells)
setattr(topologic.CellComplex, "GetTraces", GetTraces)
setattr(topologic.CellComplex, "ApplyDictionary", ApplyDictionary)
