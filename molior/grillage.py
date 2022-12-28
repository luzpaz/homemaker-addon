import ifcopenshell.api
import numpy

from topologist.helpers import string_to_coor, el
from topologic import Face, Vertex
from molior.baseclass import BaseClass
from molior.geometry import map_to_2d, matrix_align
from molior.ifc import (
    add_face_topology_epsets,
    create_face_surface,
    create_extruded_area_solid2,
    assign_storey_byindex,
    get_material_by_name,
    get_context_by_name,
    get_type_object,
)

run = ifcopenshell.api.run


class Grillage(BaseClass):
    """planar feature consisting of repeated linear elements"""

    def __init__(self, args=None):
        if args is None:
            args = {}
        super().__init__(args)
        self.ifc = "IfcBuildingElementProxy"
        self.structural_material = "Concrete"
        self.spacing = 0.45
        self.angle = 90.0
        self.inner = 0.0
        for arg in args:
            self.__dict__[arg] = args[arg]

    def execute(self):
        """Generate some ifc"""
        reference_context = get_context_by_name(
            self.file, context_identifier="Reference"
        )
        body_context = get_context_by_name(self.file, context_identifier="Body")

        aggregate = run(
            "root.create_entity",
            self.file,
            ifc_class="IfcElementAssembly",
            name=self.name,
        )
        run(
            "geometry.edit_object_placement",
            self.file,
            product=aggregate,
        )

        elevation = None
        for face in self.hull.faces:
            vertices = [[*string_to_coor(node_str)] for node_str in face[0]]
            normal = face[1]["face"].Normal()
            # need this for boundaries
            nodes_2d, matrix, normal_x = map_to_2d(vertices, normal)
            # need this for structure
            face_surface = create_face_surface(self.file, vertices, normal)
            for vertex in vertices:
                if elevation == None or vertex[2] < elevation:
                    elevation = el(vertex[2])

            face_aggregate = run(
                "root.create_entity",
                self.file,
                ifc_class="IfcElementAssembly",
                name=self.name,
            )
            run(
                "aggregate.assign_object",
                self.file,
                product=face_aggregate,
                relating_object=aggregate,
            )
            add_face_topology_epsets(
                self.file,
                face_aggregate,
                face[1]["face"],
                face[1]["back_cell"],
                face[1]["front_cell"],
            )
            run(
                "geometry.edit_object_placement",
                self.file,
                product=face_aggregate,
                matrix=matrix,
            )

            if face_aggregate.is_a("IfcVirtualElement"):
                continue
            if not self.do_representation:
                continue

            # FIXME should generate Structural Curve Member for each extrusion
            # generate structural surfaces
            structural_surface = run(
                "root.create_entity",
                self.file,
                ifc_class="IfcStructuralSurfaceMember",
                name=self.style + self.name,
                predefined_type="SHELL",
            )
            add_face_topology_epsets(
                self.file,
                structural_surface,
                face[1]["face"],
                face[1]["back_cell"],
                face[1]["front_cell"],
            )
            structural_surface.Thickness = 0.2
            run(
                "structural.assign_structural_analysis_model",
                self.file,
                product=structural_surface,
                structural_analysis_model=self.structural_analysis_model,
            )
            run(
                "geometry.assign_representation",
                self.file,
                product=structural_surface,
                representation=self.file.createIfcTopologyRepresentation(
                    reference_context,
                    reference_context.ContextIdentifier,
                    "Face",
                    [face_surface],
                ),
            )
            run(
                "material.assign_material",
                self.file,
                product=structural_surface,
                material=get_material_by_name(
                    self.file,
                    self.style_object,
                    name=self.structural_material,
                    stylename=self.style,
                ),
            )

            assignment = run(
                "root.create_entity", self.file, ifc_class="IfcRelAssignsToProduct"
            )
            assignment.RelatingProduct = structural_surface
            assignment.RelatedObjects = [face_aggregate]

            # generate repeating grillage elements

            # create a Topologic Face for slicing
            topologic_face = Face.ByVertices(
                [Vertex.ByCoordinates(*node, 0.0) for node in nodes_2d]
            )
            cropped_faces, cropped_edges = topologic_face.ParallelSlice(
                self.spacing, numpy.deg2rad(self.angle)
            )

            # shift down to inner face
            matrix_inner = matrix @ matrix_align(
                [0.0, 0.0, -self.inner], [1.0, 0.0, 0.0]
            )

            type_product = get_type_object(
                self.file,
                self.style_object,
                ifc_type=self.ifc + "Type",
                stylename=self.style,
                name=self.name,
            )

            # retrieve the Material Profile Set from the Product Type
            material_profiles = []
            profile_set = None
            for association in type_product.HasAssociations:
                if association.is_a(
                    "IfcRelAssociatesMaterial"
                ) and association.RelatingMaterial.is_a("IfcMaterialProfileSet"):
                    profile_set = association.RelatingMaterial
                    material_profiles = profile_set.MaterialProfiles

            # multiple linear elements on this Face
            for cropped_edge in cropped_edges:
                # create an element to host all extrusions
                linear_element = run(
                    "root.create_entity",
                    self.file,
                    ifc_class=self.ifc,
                    name=self.name,
                )

                run(
                    "type.assign_type",
                    self.file,
                    related_object=linear_element,
                    relating_type=type_product,
                )

                start = cropped_edge.StartVertex().Coordinates()
                direction = cropped_edge.NormalisedVector()
                length = cropped_edge.Length()

                # extrude each profile in the profile set
                extrusion_list = []
                for material_profile in material_profiles:
                    extrusion = create_extruded_area_solid2(
                        self.file, material_profile, start, direction, length
                    )
                    extrusion_list.append(extrusion)

                # stuff extrusions into a Shape Representation for the Element
                shape_representation = self.file.createIfcShapeRepresentation(
                    body_context,
                    body_context.ContextIdentifier,
                    "SweptSolid",
                    extrusion_list,
                )
                # TODO Axis Representation
                run(
                    "geometry.assign_representation",
                    self.file,
                    product=linear_element,
                    representation=shape_representation,
                )
                run(
                    "material.assign_material",
                    self.file,
                    product=linear_element,
                    material=profile_set,
                )

                # apparently aggregated elements need to be placed independently of the aggregate
                run(
                    "geometry.edit_object_placement",
                    self.file,
                    product=linear_element,
                    matrix=matrix_inner,
                )

                # stuff the element into the face aggregate
                run(
                    "aggregate.assign_object",
                    self.file,
                    product=linear_element,
                    relating_object=face_aggregate,
                )

        level = 0
        if elevation in self.elevations:
            level = self.elevations[elevation]
        assign_storey_byindex(self.file, aggregate, self.building, level)
