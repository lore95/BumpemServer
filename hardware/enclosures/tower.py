"""Tower profile and fasteners, in mm. Source: docs/knowledge/hardware.md (90x90 light B-type, slot 10).
Every printed part takes its mounting dimensions from here; correct a value once, regenerate all parts."""

FACE = 90.0            # profile face width (measured)
SLOT_PITCH = 45.0      # two slots per face, centres 22.5 mm from each edge (45 grid)
SLOT_OPEN = 10.0       # slot opening at the surface (B-type slot 10)

BOLT = "M6"            # ISO 7380 button head, 4 mm hex key (measured)
BOLT_HOLE = 6.6        # M6 clearance hole (ISO 273 medium)
HEAD_D = 10.5          # ISO 7380 M6 head diameter

PLATE_T = 5.0          # plastic under the bolt head
KEY_H = 2.5            # key depth into the slot opening; must stay below the slot lip so the T-nut clamps
KEY_CLEAR = 0.2        # per side, printed key vs SLOT_OPEN (test_fit.stl prints 3 variants)
