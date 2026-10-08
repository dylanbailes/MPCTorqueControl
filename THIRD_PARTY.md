# Third-party material

The root MIT license covers the original code and documentation in this
repository, including the project-authored custom CAD geometry in
`hardware/cad/custom/`. Its manifest identifies each exported asset; linked
supplier geometry is omitted. Dependencies retain their own licenses; they are installed from
the requirements files rather than vendored.

Downloaded models from ST, McMaster-Carr, GrabCAD, and other CAD sources are
local reference material. They are excluded through `hardware/cad/step/`
and `hardware/cad/stl/` in `.gitignore`. Their redistribution terms have not
been established, and the project does not claim ownership of them. See
[the CAD notes](hardware/cad/README.md) for the reference inventory.

Manufacturer names, product names, and linked specifications identify design
references. They do not imply endorsement. Confirm dimensions, electrical
ratings, and license terms at the source before importing or redistributing
third-party assets.
