"""Overloads domain-specific methods onto topologic.Face"""

from functools import lru_cache
import topologic
from topologic import Vertex, Edge, Face, Cluster, FaceUtility, CellUtility
from topologist.helpers import el
import topologist.ugraph as ugraph


def ByVertices(vertices):
    """Create a Face from an ordered set of Vertices"""
    edges_ptr = []
    for i in range(len(vertices) - 1):
        v1 = vertices[i]
        v2 = vertices[i + 1]
        e1 = Edge.ByStartVertexEndVertex(v1, v2)
        edges_ptr.append(e1)
    # connect the last vertex to the first one
    v1 = vertices[len(vertices) - 1]
    v2 = vertices[0]
    e1 = Edge.ByStartVertexEndVertex(v1, v2)
    edges_ptr.append(e1)
    return Face.ByEdges(edges_ptr)


setattr(topologic.Face, "ByVertices", ByVertices)


@lru_cache(maxsize=256)
def CellsOrdered(self, host_topology):
    """Front Cell and back Cell, can be None"""
    centroid = FaceUtility.InternalVertex(self, 0.001).Coordinates()
    normal = self.Normal()
    vertex_front = Vertex.ByCoordinates(
        centroid[0] + (normal[0] / 10),
        centroid[1] + (normal[1] / 10),
        centroid[2] + (normal[2] / 10),
    )
    vertex_back = Vertex.ByCoordinates(
        centroid[0] - (normal[0] / 10),
        centroid[1] - (normal[1] / 10),
        centroid[2] - (normal[2] / 10),
    )

    results = [None, None]
    if host_topology:
        cells_ptr = self.Cells_Cached(host_topology)
        for cell in cells_ptr:
            if CellUtility.Contains(cell, vertex_front, 0.001) == 0:
                results[0] = cell
            elif CellUtility.Contains(cell, vertex_back, 0.001) == 0:
                results[1] = cell
    return results


def VerticesPerimeter(self, vertices_ptr):
    """Vertices, tracing the outer perimeter"""
    return self.ExternalBoundary().Vertices(None, vertices_ptr)


def BadNormal(self, cellcomplex):
    """Faces on outside of CellComplex are orientated correctly, but 'outside'
    Faces inside the CellComplex have random orientation. Tag them with 'badnormal'
    if Face doesn't face 'out'"""
    if not self.IsWorld(cellcomplex):
        cells = self.CellsOrdered(cellcomplex)
        if cells[0] == None or cells[1] == None:
            self.Set("badnormal", True)
            return True
        if cells[1].IsOutside() and not cells[0].IsOutside():
            self.Set("badnormal", True)
            return True
    return False


def IsVertical(self):
    normal_stl = FaceUtility.NormalAtParameters(self, 0.5, 0.5)
    if abs(normal_stl[2]) < 0.0001:
        return True
    return False


def IsHorizontal(self):
    normal_stl = FaceUtility.NormalAtParameters(self, 0.5, 0.5)
    if abs(normal_stl[2]) > 0.9999:
        return True
    return False


def IsUpward(self):
    normal = self.Normal()
    if normal[2] > 0.0:
        return True
    return False


def AxisOuter(self):
    """2D bottom edge of a vertical face, for external walls, anti-clockwise in plan"""
    edges_ptr = []
    self.EdgesBottom(edges_ptr)
    if len(edges_ptr) > 0:
        unordered = ugraph.graph()
        for edge in edges_ptr:
            start_coor = edge.StartVertex().CoorAsString()
            end_coor = edge.EndVertex().CoorAsString()
            unordered.add_edge(
                {
                    start_coor: [
                        end_coor,
                        {
                            "start_vertex": edge.StartVertex(),
                            "end_vertex": edge.EndVertex(),
                        },
                    ]
                }
            )
        ordered = unordered.find_chains()[0]
        ordered_edges = ordered.edges()
        first_edge = ordered_edges[0][0]
        last_edge = ordered_edges[-1][0]
        if self.Get("badnormal"):
            return [
                ordered.graph[first_edge][1]["end_vertex"],
                ordered.graph[last_edge][1]["start_vertex"],
            ]
        else:
            return [
                ordered.graph[first_edge][1]["start_vertex"],
                ordered.graph[last_edge][1]["end_vertex"],
            ]


# FIXME doesn't appear to be in use
def AxisOuterTop(self):
    """2D top edge of a vertical face, for external walls, anti-clockwise in plan"""
    edges_ptr = []
    self.EdgesTop(edges_ptr)
    if len(edges_ptr) > 0:
        unordered = ugraph.graph()
        for edge in edges_ptr:
            start_coor = edge.StartVertex().CoorAsString()
            end_coor = edge.EndVertex().CoorAsString()
            unordered.add_edge(
                {
                    start_coor: [
                        end_coor,
                        {
                            "start_vertex": edge.StartVertex(),
                            "end_vertex": edge.EndVertex(),
                        },
                    ]
                }
            )
        ordered = unordered.find_chains()[0]
        ordered_edges = ordered.edges()
        first_edge = ordered_edges[0][0]
        last_edge = ordered_edges[-1][0]
        if self.Get("badnormal"):
            return [
                ordered.graph[last_edge][1]["start_vertex"],
                ordered.graph[first_edge][1]["end_vertex"],
            ]
        else:
            return [
                ordered.graph[last_edge][1]["end_vertex"],
                ordered.graph[first_edge][1]["start_vertex"],
            ]


@lru_cache(maxsize=256)
def IsInternal(self, host_topology):
    """Face between two indoor cells"""
    cells_ptr = self.Cells_Cached(host_topology)
    if len(cells_ptr) == 2:
        for cell in cells_ptr:
            if cell.IsOutside():
                return False
        return True
    return False


@lru_cache(maxsize=256)
def IsExternal(self, host_topology):
    """Face between indoor cell and outdoor cell (or world)"""
    cells_ptr = self.Cells_Cached(host_topology)
    if len(cells_ptr) == 2:
        if cells_ptr[0].IsOutside() and not cells_ptr[1].IsOutside():
            return True
        if cells_ptr[1].IsOutside() and not cells_ptr[0].IsOutside():
            return True
    elif len(cells_ptr) == 1:
        if not cells_ptr[0].IsOutside():
            return True
    return False


@lru_cache(maxsize=256)
def IsWorld(self, host_topology):
    """Face on outside of mesh"""
    cells_ptr = self.Cells_Cached(host_topology)
    if len(cells_ptr) == 1:
        return True
    return False


@lru_cache(maxsize=256)
def IsOpen(self, host_topology):
    """Face on outdoor cell on outside of mesh"""
    cells_ptr = self.Cells_Cached(host_topology)
    if len(cells_ptr) == 1:
        for cell in cells_ptr:
            if cell.IsOutside():
                return True
    return False


# FIXME doesn't appear to be in use
def FaceAbove(self, host_topology):
    """Does this Face have a vertical Face attached to a horizontal top Edge?"""
    edges_ptr = []
    self.EdgesTop(edges_ptr)
    for edge in edges_ptr:
        faces_ptr = edge.Faces_Cached(host_topology)
        for face in faces_ptr:
            if face.IsVertical() and not face.IsSame(self):
                return face
    return None


def FacesBelow(self, host_topology):
    """Does this Face have Faces attached below a horizontal bottom Edge?"""
    edges_ptr = []
    self.EdgesBottom(edges_ptr)
    result = []
    for edge in edges_ptr:
        faces_below = edge.FacesBelow(host_topology)
        if faces_below:
            result.extend(faces_below)
    return result


def CellsBelow(self, host_topology):
    """Does this Face have Cells attached below a horizontal bottom Edge?"""
    edges_ptr = []
    self.EdgesBottom(edges_ptr)
    result = []
    for edge in edges_ptr:
        cells_below = edge.CellsBelow(host_topology)
        if cells_below:
            result.extend(cells_below)
    return result


def CellAbove(self, host_topology):
    """Is this Face a floor for a Cell above, return it"""
    if not self.IsVertical():
        cells = self.Cells_Cached(host_topology)
        if len(cells) == 2:
            if cells[0].Centroid().Z() > cells[1].Centroid().Z():
                return cells[0]
            return cells[1]
        elif len(cells) == 1 and cells[0].Centroid().Z() > self.Centroid().Z():
            return cells[0]
    return None


# FIXME doesn't appear to be in use
def HorizontalFacesSideways(self, host_topology):
    """Which horizontal faces are attached to the bottom Edges of this Face?"""
    edges_ptr = []
    self.EdgesBottom(edges_ptr)
    result_faces_ptr = []
    for edge in edges_ptr:
        faces_ptr = edge.Faces_Cached(host_topology)
        for face in faces_ptr:
            if face.IsHorizontal() and not face.IsSame(self):
                result_faces_ptr.append(face)
    return result_faces_ptr


def Normal(self):
    """Normal for this Face, but flipped if tagged with 'badnormal'"""
    normal_stl = FaceUtility.NormalAtParameters(self, 0.5, 0.5)
    if self.Get("badnormal"):
        return [-normal_stl[0], -normal_stl[1], -normal_stl[2]]
    else:
        return [normal_stl[0], normal_stl[1], normal_stl[2]]


def TopLevelConditions(self, host_topology):
    """Assuming this is a vertical external wall, how do the top edges continue?"""
    # TODO traces where face above is open
    result = []
    edges_ptr = []
    self.EdgesTop(edges_ptr)
    for edge in edges_ptr:
        faces_ptr = edge.FacesWorld(host_topology)
        for (
            face
        ) in faces_ptr:  # there should only be one external face (not including self)
            if face.IsSame(self):
                continue
            # top face tilts backward (roof) if normal faces up, forward (soffit) if faces down
            normal = face.Normal()
            condition = "top"
            if abs(normal[2]) < 0.0001:
                condition += "-vertical"
            elif normal[2] > 0.0:
                condition += "-backward"
            else:
                condition += "-forward"
            # top face can be above or below top edge
            if abs(normal[2]) > 0.9999:
                condition += "-level"
            elif face.Centroid().Z() > edge.Centroid().Z():
                condition += "-up"
            else:
                condition += "-down"
            result.append([edge, condition])
    return result


def BottomLevelConditions(self, host_topology):
    """Assuming this is a vertical external wall, how do the bottom edges continue?"""
    # TODO traces where face below is open
    result = []
    edges_ptr = []
    self.EdgesBottom(edges_ptr)
    for edge in edges_ptr:
        faces_ptr = edge.FacesWorld(host_topology)
        for (
            face
        ) in faces_ptr:  # there should only be one external face (not including self)
            if face.IsSame(self):
                continue
            # bottom face tilts forward (roof) if normal faces up, backward (soffit) if faces down
            normal = face.Normal()
            condition = "bottom"
            if abs(normal[2]) < 0.0001:
                condition += "-vertical"
            elif normal[2] > 0.0:
                condition += "-forward"
            else:
                condition += "-backward"
            # bottom face can be above or below bottom edge
            if abs(normal[2]) > 0.9999:
                condition += "-level"
            elif face.Centroid().Z() > edge.Centroid().Z():
                condition += "-up"
            else:
                condition += "-down"
            result.append([edge, condition])
    return result


def EdgesTop(self, result_edges_ptr):
    """A list of horizontal edges at the highest level of this face"""
    edges_ptr = []
    self.Edges(None, edges_ptr)
    level = el(self.Elevation() + self.Height())
    for edge in edges_ptr:
        vertex_start = edge.StartVertex()
        vertex_end = edge.EndVertex()
        if el(vertex_start.Z()) == level and el(vertex_end.Z()) == level:
            result_edges_ptr.append(edge)


def EdgesBottom(self, result_edges_ptr):
    """A list of horizontal edges at the lowest level of this face"""
    edges_ptr = []
    self.Edges(None, edges_ptr)
    level = self.Elevation()
    for edge in edges_ptr:
        vertex_start = edge.StartVertex()
        vertex_end = edge.EndVertex()
        if el(vertex_start.Z()) == level and el(vertex_end.Z()) == level:
            result_edges_ptr.append(edge)


def EdgesCrop(self, result_edges_ptr):
    """Which edges are not vertical or top/bottom?"""
    edges_ptr = []
    self.ExternalBoundary().Edges(None, edges_ptr)
    bottom = self.Elevation()
    top = el(self.Elevation() + self.Height())
    for edge in edges_ptr:
        vertex_start = edge.StartVertex()
        vertex_end = edge.EndVertex()
        if el(vertex_start.Z()) == top and el(vertex_end.Z()) == top:
            continue
        elif el(vertex_start.Z()) == bottom and el(vertex_end.Z()) == bottom:
            continue
        elif edge.IsVertical():
            continue
        result_edges_ptr.append(edge)


def ParallelSlice(self, inc=0.45, degrees=90):
    """Crop a face with parallel lines"""
    vertices = []
    self.Vertices(None, vertices)
    minx = min(node.Coordinates()[0] for node in vertices)
    maxx = max(node.Coordinates()[0] for node in vertices)
    miny = min(node.Coordinates()[1] for node in vertices)
    maxy = max(node.Coordinates()[1] for node in vertices)
    # create Topologic Edges for slicing the Face
    cutting_edges = []
    x = minx
    # FIXME set start and angle of linear elements
    while x < maxx:
        cutting_edges.append(
            Edge.ByStartVertexEndVertex(
                *[Vertex.ByCoordinates(x, y, 0.0) for y in [miny, maxy]]
            )
        )
        x += inc
    shell = self.Slice(Cluster.ByTopologies(cutting_edges))
    topologic_faces = []
    shell.Faces(None, topologic_faces)
    topologic_edges = []
    shell.Edges(None, topologic_edges)
    cropped_edges = []
    for topologic_edge in topologic_edges:
        myfaces = []
        topologic_edge.Faces(shell, myfaces)
        if len(myfaces) == 2:
            cropped_edges.append(topologic_edge)
    return topologic_faces, cropped_edges


setattr(topologic.Face, "CellsOrdered", CellsOrdered)
setattr(topologic.Face, "VerticesPerimeter", VerticesPerimeter)
setattr(topologic.Face, "BadNormal", BadNormal)
setattr(topologic.Face, "IsVertical", IsVertical)
setattr(topologic.Face, "IsHorizontal", IsHorizontal)
setattr(topologic.Face, "IsUpward", IsUpward)
setattr(topologic.Face, "AxisOuter", AxisOuter)
setattr(topologic.Face, "AxisOuterTop", AxisOuterTop)
setattr(topologic.Face, "IsInternal", IsInternal)
setattr(topologic.Face, "IsExternal", IsExternal)
setattr(topologic.Face, "IsWorld", IsWorld)
setattr(topologic.Face, "IsOpen", IsOpen)
setattr(topologic.Face, "FaceAbove", FaceAbove)
setattr(topologic.Face, "FacesBelow", FacesBelow)
setattr(topologic.Face, "CellsBelow", CellsBelow)
setattr(topologic.Face, "CellAbove", CellAbove)
setattr(topologic.Face, "HorizontalFacesSideways", HorizontalFacesSideways)
setattr(topologic.Face, "Normal", Normal)
setattr(topologic.Face, "TopLevelConditions", TopLevelConditions)
setattr(topologic.Face, "BottomLevelConditions", BottomLevelConditions)
setattr(topologic.Face, "EdgesTop", EdgesTop)
setattr(topologic.Face, "EdgesBottom", EdgesBottom)
setattr(topologic.Face, "EdgesCrop", EdgesCrop)
setattr(topologic.Face, "ParallelSlice", ParallelSlice)
