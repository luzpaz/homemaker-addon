User Reference
==============

Traces
------

Traces are 2D closed or open chains that define building elements,
differentiated by elevation, height and style properties, typically running in
an anti-clockwise direction, these follow the outlines of rooms, walls, eaves,
string-courses etc.. All possible traces are made available when the
CellComplex defining the building is processed.

There are traces for each space/room usage:

* kitchen
* living
* bedroom
* toilet
* sahn (an outside circulation space)
* circulation
* stair
* retail
* outside
* void (an internal space that doesn't qualify as a room)

There are traces for each wall condition:

* external
* internal (these are always a single segment long)
* open (an external 'wall' to outside space)

There are traces that follow the top and bottom horizontal edges of
external walls:

* top-vertical-up (a string course between two vertical walls)
* top-forward-up
* top-forward-level (a horizontal soffit at the top of a wall)
* top-forward-down
* top-backward-up (a typical eave with a pitched roof above)
* top-backward-level (a typical eave with a horizontal roof behind)
* top-backward-down (a typical eave at the top of a monopitch roof)
* bottom-vertical-down (a string course between two vertical walls)
* bottom-forward-up (a box gutter where a pitched roof meets a wall)
* bottom-forward-level (a wall on a flat roof)
* bottom-forward-down (a wall above a lean-to pitched roof)
* bottom-backward-up
* bottom-backward-level (a horizontal soffit behind a wall)
* bottom-backward-down

And traces that follow the bottom of internal walls with nothing
below, or nothing but cells below:

* internal-footing (always one segment long)
* internal-beam (always one segment long)

Wall
~~~~

A vertical wall, internal or external

Extrusion
~~~~~~~~~

A profile following a horizontal 2D path

Space
~~~~~

A room or outside volume, as a 2D path extruded vertically

Floor
~~~~~

A floor filling a room or Space_

Repeat
~~~~~~

A row of evenly spaced identical objects. The gaps between these objects can be
optionally defined by further Grillage_ or Extrusion_ elements, allowing
recursive build-up of complex construction systems.

Stair
~~~~~

A stair filling a single storey extruded space (TBC)

Hulls
-----

Hulls are 3D shells that define planar building elements, differentiated by
style and orientation.  Typically these define roofs, soffits etc.. that can't
be described by Traces_, and are drawn using a simple thickened plate or
grillage corresponding to the original Face.  All possible hulls are made
available when the CellComplex defining the building is processed.

There are hulls for these conditions:

* external-panel (a vertical wall that doesn't have a horizontal bottom edge)
* internal-panel (a vertical wall that doesn't have a horizontal bottom edge)
* flat (a flat roof)
* roof (an inclined roof)
* soffit (a non-vertical soffit)
* vault (a non-vertical divider between internal spaces)

In addition, there are hulls that correspond to identically named traces:

* Each wall condition with horizontal bottom edges:

  * external (a vertical wall between inside and outside)
  * internal (a vertical wall between two internal spaces)
  * open (an external 'wall' to outside space)

* Each cell floor perimeter, note that internal shell faces have no up or down
  orientation, use the equivalent trace instead:

  * kitchen
  * living
  * bedroom
  * toilet
  * sahn (an outside circulation space)
  * circulation
  * stair
  * retail
  * outside
  * void (an internal space that doesn't qualify as a room)

Shell
~~~~~

A pitched roof, planar surface or soffit

Grillage
~~~~~~~~

A planar feature consisting of repeated linear elements. These linear elements
are optionally defined by Extrusion_ and/or Repeat_ Traces_. The areas sliced
by these linear elements can be optionally defined by Shell_ and/or Grillage_
Hulls_.

Since Repeat_ and Grillage_ elements are recursive, complex construction
systems can be built up through layering.

Styles
------

A 'style' is defined by a collection of YAML configuration files and other file
resources in a folder.

Each subfolder has a unique name and represents a different architectural
'style', buildings can be all one style or have multiple styles, each applied
to different parts of the building.  Styles are inherited from parent folders,
and can represent only minor variations, without needing to duplicate anything
that is already defined by the parent folder(s).

Alternative styles are accessed by a stylename, each represented by a subfolder
that inherits data and resources from all parent folders.  For example, a style
named 'thin' may be found in a folder named ``${share_dir}/rustic/wood/thin``; any
query for 'thin' data not found in this folder will be sought in
``${share_dir}/rustic/wood``; failing that it will be sought in
``${share_dir}/rustic``, and finally in ``${share_dir}`` itself.

In the Blender add-on styles are assigned by creating Blender materials with
names matching the stylename.  These material names are propagated into the
Topologic CellComplex, and are used to segment the Traces_ and Hulls_ by style.

Note that styles are accessed by their short stylename *not* the path, this
allows inheritance to be defined entirely by rearrangement of the configuration
data.  This also means that there may only be one folder called 'thin' in the
folder tree, all others will be ignored.


Custom style location
~~~~~~~~~~~~~~~~~~~~~

The addon ships with some example styles in the `share` folder installed with
the software. You can edit or add styles there, or use *Select Style Directory*
in the add-on preferences to indicate a different location to look for style
definitions - either copy over some example styles and edit them here, or start
with an empty folder and build a new style from scratch (note that an empty
style definition will result in an empty IFC model without any Building
Elements).

library.ifc
~~~~~~~~~~~

The ``library.ifc`` file contains IFC Type definitions for the style.  Types
define 3D geometry, 2D profiles, layersets, materials, usage and psets for
building elements such as windows, walls, beams, columns, mouldings etc...

This file is a collection of these Types and can be modified using a Native IFC
editor.  Type definitions are accessed from the configuration files using the
Class and Name pair as key, e.g. if your library has two 'IfcDoor' Types called
'shopfront', only the first one will be available.  A different style may also
provide an 'IfcDoor' 'shopfront' Type, these co-exist in the generated IFC
model in separate named Project Libraries.

Only Type definitions that are requested are copied into named Project
Libraries in the generated IFC model.

This file does not need to contain all the Type assets used by this style.  If
a Class and Name combination can't be found, then this Type definition will be
recursively retrieved from the parent style.  This allows the designer to
create a custom style where only a single item is different.

hulls.yml
~~~~~~~~~

Items in ``hulls.yml`` represent a method of construction that fills a 3D planar
polygonal element organised by *Name*.  The ``ifc`` parameter indicates the *IFC
Type* to be used, the ``class`` indicates whether a Shell_ or Grillage_ is
requested, and the ``condition`` matches to geometrical status of the element
(See Hulls_ above).

A ``condition`` can be matched by multiple items in this list, e.g. to generate a
Grillage_ representing a stud wall covered by a Shell_ representing a
covering board.  Sometimes a hull defined by a parent style is unwanted, this
can be overridden by creating a hull definition with the same *Name*, but with
an invalid ``condition`` (such as ``noop``).

traces.yml
~~~~~~~~~~

Items in ``traces.yml`` represent a method of construction that follows a 2D
path, organised by *Name*.  The ``ifc`` parameter indicates the *IFC Type* to be
used, the ``class`` indicates whether a Wall_, Extrusion_, Space_, Floor_,
Repeat_ or Stair_ is requested, and the ``condition`` matches to geometrical
status of the element (See Traces_ above).

A ``condition`` can be matched by multiple items in this list, e.g. to generate a
Wall_ decorated by a Repeat_ representing a bracket.  Sometimes a trace
defined by a parent style is unwanted, this can be overridden by creating a
trace definition with the same *Name*, but with an invalid ``condition`` (such as
``noop``).

families.yml
~~~~~~~~~~~~

3D assets are contained in ``library.ifc``, where each Type (a single size of
window, door, column etc...) has Representations, Materials, Psets etc..  These
assets are referenced by *Class* and *Name* in the ``families.yml`` file.  This
additional layer of reference allows a window, for example, to be defined by
one or more sizes which are dynamically fitted to the available space.

openings.yml
~~~~~~~~~~~~

Each item in ``openings.yml`` represents a series of hard-coded names that select
window or door families from the ``families.yml`` file.

Note, this file will change or be removed in the future.
