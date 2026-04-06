#!/usr/bin/env python3
"""
81개 CAD/기계 부품 카테고리에 대한 상세 메타데이터.

CLIP v2 캡션 풍부화(enrich_captions.py)에 사용됨.
각 카테고리에 대해:
  - aliases: 카테고리의 다양한 명칭 (캡션 다양성 극대화)
  - features: 도면에서 볼 수 있는 형상/특징
  - applications: 이 부품의 용도/적용 분야

카테고리 출처: unified_class_names.json (index 0-84, 70/71 제외)
"""

CATEGORY_DETAILS = {
    # === MiSUMi 기계 부품 (0-55) ===
    "Accessories": {
        "aliases": [
            "mechanical accessory", "machine accessory", "assembly accessory",
            "hardware fitting", "mounting accessory", "machine component",
        ],
        "features": [
            "mounting hole", "threaded bore", "flat surface",
            "fastening point", "assembly interface", "slot pattern",
        ],
        "applications": [
            "machine assembly", "equipment mounting", "fixture attachment",
            "mechanical assembly", "component integration",
        ],
    },
    "Actuator": {
        "aliases": [
            "actuator unit", "linear actuator", "rotary actuator",
            "pneumatic actuator", "electric actuator", "servo actuator",
            "drive actuator", "motion actuator",
        ],
        "features": [
            "piston rod", "cylinder body", "stroke length",
            "mounting bracket", "port connection", "end cap",
            "rod seal", "stroke indicator",
        ],
        "applications": [
            "linear motion control", "automation system", "positioning mechanism",
            "robotic actuation", "valve operation",
        ],
    },
    "Aluminum_Frames": {
        "aliases": [
            "aluminum extrusion", "aluminum profile", "structural frame",
            "T-slot frame", "extruded aluminum", "aluminum rail",
            "modular frame", "aluminum structural member",
        ],
        "features": [
            "T-slot channel", "cross-section profile", "corner bracket",
            "mounting groove", "internal cavity", "extrusion profile",
            "slot opening", "ribbed structure",
        ],
        "applications": [
            "machine frame construction", "workstation structure", "enclosure frame",
            "linear motion frame", "automation framework",
        ],
    },
    "Angles": {
        "aliases": [
            "angle bracket", "L-bracket", "corner angle",
            "mounting angle", "structural angle", "angle plate",
        ],
        "features": [
            "90-degree bend", "mounting holes", "flange surface",
            "equal leg", "unequal leg", "bolt pattern",
        ],
        "applications": [
            "corner reinforcement", "structural support", "right-angle mounting",
            "frame connection", "bracket assembly",
        ],
    },
    "Antivibration": {
        "aliases": [
            "vibration damper", "vibration isolator", "anti-vibration mount",
            "shock absorber mount", "rubber isolator", "damping pad",
            "vibration absorber", "isolation mount",
        ],
        "features": [
            "rubber element", "steel plate", "threaded stud",
            "damping layer", "spring rate", "compression pad",
        ],
        "applications": [
            "vibration isolation", "shock absorption", "noise reduction",
            "machine mounting", "equipment damping",
        ],
    },
    "Ball_Screws": {
        "aliases": [
            "ball screw assembly", "ball screw shaft", "recirculating ball screw",
            "precision ball screw", "lead screw", "ball screw unit",
        ],
        "features": [
            "screw shaft", "ball nut", "ball groove", "thread pitch",
            "return tube", "seal ring", "flange mount",
        ],
        "applications": [
            "precision linear motion", "CNC machine axis", "positioning system",
            "servo drive mechanism", "high-precision feed",
        ],
    },
    "Ball_Splines": {
        "aliases": [
            "ball spline shaft", "spline bearing", "linear ball spline",
            "torque-transmitting spline", "rotary ball spline",
        ],
        "features": [
            "spline groove", "ball track", "outer cylinder",
            "torque flange", "retainer ring", "spline shaft",
        ],
        "applications": [
            "rotary and linear motion", "torque transmission", "precision indexing",
            "robotic arm joint", "spindle mechanism",
        ],
    },
    "Bearings_with_Holder": {
        "aliases": [
            "pillow block bearing", "mounted bearing unit", "bearing housing",
            "plummer block", "bearing pedestal", "flanged bearing unit",
            "bearing block", "housed bearing",
        ],
        "features": [
            "inner ring", "outer housing", "mounting bolt holes",
            "set screw", "grease fitting", "seal cover",
            "shaft bore", "base plate",
        ],
        "applications": [
            "shaft support", "rotating machinery", "conveyor roller support",
            "power transmission bearing", "fan shaft mounting",
        ],
    },
    "Brackets": {
        "aliases": [
            "mounting bracket", "support bracket", "metal bracket",
            "fixing bracket", "shelf bracket", "U-bracket",
        ],
        "features": [
            "mounting holes", "bent flange", "reinforcing rib",
            "slot pattern", "welded joint", "gusset plate",
        ],
        "applications": [
            "component mounting", "structural support", "panel fixing",
            "sensor bracket", "motor bracket",
        ],
    },
    "Casters": {
        "aliases": [
            "caster wheel", "swivel caster", "fixed caster",
            "industrial caster", "heavy-duty caster", "roller caster",
        ],
        "features": [
            "wheel", "swivel plate", "axle bolt",
            "brake lever", "mounting plate", "wheel tread",
        ],
        "applications": [
            "mobile equipment", "cart wheel", "workstation mobility",
            "material handling", "rolling platform",
        ],
    },
    "Clamps": {
        "aliases": [
            "clamping device", "toggle clamp", "pipe clamp",
            "bar clamp", "shaft clamp", "quick clamp",
        ],
        "features": [
            "clamping arm", "pivot point", "handle lever",
            "mounting base", "pressure pad", "locking mechanism",
        ],
        "applications": [
            "workpiece holding", "fixture clamping", "pipe securing",
            "jig assembly", "tool holding",
        ],
    },
    "Contact_Probes": {
        "aliases": [
            "test probe", "spring-loaded probe", "pogo pin",
            "contact pin", "probe needle", "test point probe",
        ],
        "features": [
            "probe tip", "spring mechanism", "barrel body",
            "receptacle", "contact point", "plunger stroke",
        ],
        "applications": [
            "electronic testing", "PCB probing", "circuit board test",
            "contact inspection", "signal measurement",
        ],
    },
    "Conveyors": {
        "aliases": [
            "conveyor system", "belt conveyor", "roller conveyor",
            "chain conveyor", "transport conveyor", "material conveyor",
        ],
        "features": [
            "belt track", "drive roller", "idler roller",
            "side guide", "tension adjuster", "frame rail",
        ],
        "applications": [
            "material transport", "production line", "package handling",
            "assembly line conveying", "automated logistics",
        ],
    },
    "Couplings": {
        "aliases": [
            "shaft coupling", "flexible coupling", "rigid coupling",
            "jaw coupling", "disc coupling", "oldham coupling",
            "beam coupling", "bellows coupling",
        ],
        "features": [
            "hub bore", "keyway slot", "set screw hole",
            "flexible element", "clamp collar", "coupling insert",
        ],
        "applications": [
            "shaft connection", "torque transmission", "misalignment compensation",
            "motor-to-shaft coupling", "drive train connection",
        ],
    },
    "Cover_Panels": {
        "aliases": [
            "cover plate", "panel cover", "protective cover",
            "enclosure panel", "shield plate", "guard cover",
        ],
        "features": [
            "flat surface", "mounting screw holes", "edge bend",
            "ventilation slot", "cutout opening", "panel frame",
        ],
        "applications": [
            "equipment protection", "enclosure panel", "safety guard",
            "dust protection", "access cover",
        ],
    },
    "Cylinders": {
        "aliases": [
            "pneumatic cylinder", "hydraulic cylinder", "air cylinder",
            "actuating cylinder", "piston cylinder", "compact cylinder",
            "double-acting cylinder", "single-acting cylinder",
        ],
        "features": [
            "cylinder barrel", "piston rod", "end cap",
            "port fitting", "rod seal", "cushion mechanism",
            "mounting flange", "stroke length",
        ],
        "applications": [
            "linear actuation", "clamping force", "pressing operation",
            "lift mechanism", "automated machine actuation",
        ],
    },
    "Fitting_and_Nozzles": {
        "aliases": [
            "pipe fitting", "hose fitting", "nozzle assembly",
            "tube connector", "fluid connector", "coupling fitting",
            "spray nozzle", "flow nozzle",
        ],
        "features": [
            "thread connection", "bore passage", "hex body",
            "O-ring groove", "barb end", "flare fitting",
        ],
        "applications": [
            "fluid connection", "piping system", "pneumatic line",
            "hydraulic connection", "coolant delivery",
        ],
    },
    "Flat_Belts_and_Round_Belts": {
        "aliases": [
            "flat belt", "round belt", "timing belt",
            "drive belt", "power transmission belt", "conveyor belt",
        ],
        "features": [
            "belt width", "belt thickness", "pulley groove",
            "tension side", "slack side", "belt joint",
        ],
        "applications": [
            "power transmission", "conveyor drive", "speed reduction",
            "machine drive system", "material transport belt",
        ],
    },
    "Gears": {
        "aliases": [
            "gear wheel", "spur gear", "helical gear",
            "bevel gear", "worm gear", "cogwheel",
            "pinion gear", "rack gear",
        ],
        "features": [
            "teeth profile", "pitch circle", "bore hole",
            "keyway", "hub face", "tooth module",
            "pressure angle", "addendum circle",
        ],
        "applications": [
            "power transmission", "speed reduction", "torque conversion",
            "rotary motion transfer", "gear train mechanism",
        ],
    },
    "Heaters": {
        "aliases": [
            "cartridge heater", "band heater", "strip heater",
            "immersion heater", "heating element", "industrial heater",
        ],
        "features": [
            "heating coil", "terminal lead", "sheath body",
            "mounting bracket", "thermocouple port", "watt density",
        ],
        "applications": [
            "mold heating", "process heating", "liquid heating",
            "temperature control", "thermal processing",
        ],
    },
    "Hinge_Pins": {
        "aliases": [
            "hinge pin", "pivot pin", "clevis pin",
            "dowel pin", "retaining pin", "hinge shaft",
        ],
        "features": [
            "pin shaft", "head diameter", "pin length",
            "cotter hole", "groove ring", "chamfered end",
        ],
        "applications": [
            "hinge pivot", "linkage connection", "door hinge",
            "joint pin", "mechanical linkage",
        ],
    },
    "Holders_for_Shaft": {
        "aliases": [
            "shaft holder", "shaft support block", "shaft mount",
            "bearing holder", "shaft clamp block", "shaft bracket",
        ],
        "features": [
            "bore diameter", "mounting holes", "split design",
            "clamping screw", "base surface", "alignment face",
        ],
        "applications": [
            "shaft positioning", "shaft support", "linear shaft mount",
            "guide shaft holding", "precision shaft alignment",
        ],
    },
    "Inspections": {
        "aliases": [
            "inspection gauge", "measurement tool", "inspection fixture",
            "quality inspection tool", "test gauge", "calibration device",
        ],
        "features": [
            "measurement scale", "probe point", "reference surface",
            "dial indicator", "gauge body", "contact tip",
        ],
        "applications": [
            "quality inspection", "dimensional measurement", "surface inspection",
            "tolerance checking", "precision calibration",
        ],
    },
    "Led_Lighting": {
        "aliases": [
            "LED light", "LED strip", "LED panel",
            "LED lamp", "indicator light", "LED module",
        ],
        "features": [
            "LED chip", "heat sink", "lens cover",
            "mounting bracket", "wire terminal", "diffuser",
        ],
        "applications": [
            "machine illumination", "indicator lighting", "work area lighting",
            "inspection lighting", "signal indicator",
        ],
    },
    "Levers": {
        "aliases": [
            "lever arm", "operating lever", "clamping lever",
            "adjustable lever", "cam lever", "handle lever",
            "toggle lever", "locking lever",
        ],
        "features": [
            "lever arm", "pivot bore", "handle grip",
            "cam surface", "thread stud", "knob head",
        ],
        "applications": [
            "manual clamping", "position locking", "quick release",
            "machine operation", "lever mechanism",
        ],
    },
    "Linear_Bushings": {
        "aliases": [
            "linear bushing", "linear ball bushing", "slide bushing",
            "linear bearing", "ball bushing", "plain bushing",
        ],
        "features": [
            "inner bore", "ball groove", "outer cylinder",
            "retainer", "seal ring", "flange collar",
        ],
        "applications": [
            "linear motion guide", "shaft sliding", "smooth linear travel",
            "precision slide mechanism", "guide shaft bearing",
        ],
    },
    "Linear_Guides": {
        "aliases": [
            "linear guide rail", "linear motion guide", "slide rail",
            "LM guide", "profile rail guide", "precision guide",
        ],
        "features": [
            "rail profile", "carriage block", "ball groove",
            "mounting holes", "end seal", "grease nipple",
        ],
        "applications": [
            "precision linear motion", "CNC axis guide", "slide mechanism",
            "positioning stage", "automation slide",
        ],
    },
    "Locating_Pins": {
        "aliases": [
            "locating pin", "dowel pin", "positioning pin",
            "alignment pin", "taper pin", "spring pin",
            "roll pin", "guide pin",
        ],
        "features": [
            "pin diameter", "pin length", "chamfered tip",
            "ground surface", "head type", "tolerance grade",
        ],
        "applications": [
            "precision alignment", "jig positioning", "die alignment",
            "fixture locating", "mold pin alignment",
        ],
    },
    "Locating_and_Guide_Components": {
        "aliases": [
            "guide component", "locating fixture", "positioning guide",
            "alignment component", "guide block", "locator assembly",
        ],
        "features": [
            "guide surface", "locating bore", "datum face",
            "guide pin hole", "relief groove", "alignment slot",
        ],
        "applications": [
            "workpiece positioning", "tool guidance", "fixture alignment",
            "die set guiding", "assembly locating",
        ],
    },
    "Manifolds": {
        "aliases": [
            "pneumatic manifold", "hydraulic manifold", "valve manifold",
            "distribution manifold", "solenoid manifold", "fluid manifold",
        ],
        "features": [
            "port holes", "internal passages", "valve mounting surface",
            "supply port", "exhaust port", "mounting bolt pattern",
        ],
        "applications": [
            "pneumatic distribution", "hydraulic circuit", "valve bank mounting",
            "fluid distribution", "multi-valve control",
        ],
    },
    "Misc": {
        "aliases": [
            "miscellaneous part", "general component", "machine part",
            "mechanical element", "hardware component", "utility part",
        ],
        "features": [
            "custom geometry", "mounting feature", "functional surface",
            "fastening point", "interface dimension", "assembly feature",
        ],
        "applications": [
            "general machinery", "custom application", "special purpose",
            "machine assembly", "equipment integration",
        ],
    },
    "Oil_Free_Bushings": {
        "aliases": [
            "oil-free bushing", "self-lubricating bushing", "dry bearing",
            "sintered bushing", "composite bushing", "maintenance-free bushing",
        ],
        "features": [
            "inner bore", "outer diameter", "flange",
            "graphite plug", "lubrication groove", "split line",
        ],
        "applications": [
            "dry sliding", "maintenance-free bearing", "food machinery",
            "clean environment bearing", "low-friction sliding",
        ],
    },
    "Pipe_Frames": {
        "aliases": [
            "pipe frame structure", "tube frame", "steel pipe frame",
            "round tube frame", "pipe joint frame", "tubular frame",
        ],
        "features": [
            "pipe cross-section", "joint connector", "end fitting",
            "frame corner", "pipe clamp", "cross member",
        ],
        "applications": [
            "workstation frame", "cart frame", "rack structure",
            "material handling frame", "modular pipe structure",
        ],
    },
    "Pipes_Fitting_Valves": {
        "aliases": [
            "pipe valve", "pipe fitting", "flow control valve",
            "ball valve", "check valve", "gate valve",
            "pipe connector", "tube fitting",
        ],
        "features": [
            "valve body", "handle wheel", "threaded end",
            "seal seat", "flow passage", "flange connection",
        ],
        "applications": [
            "flow control", "piping system", "fluid shut-off",
            "pressure regulation", "process piping",
        ],
    },
    "Plungers": {
        "aliases": [
            "spring plunger", "ball plunger", "index plunger",
            "press-fit plunger", "detent plunger", "locking plunger",
        ],
        "features": [
            "plunger body", "spring mechanism", "ball tip",
            "thread shank", "knob head", "stroke travel",
        ],
        "applications": [
            "position indexing", "detent mechanism", "spring-loaded contact",
            "quick positioning", "fixture detent",
        ],
    },
    "Posts": {
        "aliases": [
            "support post", "standoff post", "spacer post",
            "pillar post", "mounting post", "column post",
        ],
        "features": [
            "cylindrical body", "threaded end", "hex section",
            "shoulder step", "post length", "knurled surface",
        ],
        "applications": [
            "panel standoff", "board mounting", "structural support",
            "component spacing", "elevated mounting",
        ],
    },
    "Pulls": {
        "aliases": [
            "pull handle", "drawer pull", "cabinet pull",
            "door handle", "knob handle", "grip pull",
        ],
        "features": [
            "handle bar", "mounting stud", "grip surface",
            "finger clearance", "pull shape", "screw hole",
        ],
        "applications": [
            "door opening", "drawer operation", "panel access",
            "equipment handle", "cabinet hardware",
        ],
    },
    "Resin_Plates": {
        "aliases": [
            "plastic plate", "resin sheet", "polymer plate",
            "engineering plastic plate", "POM plate", "acetal plate",
        ],
        "features": [
            "flat surface", "plate thickness", "machined edge",
            "hole pattern", "countersink bore", "chamfered corner",
        ],
        "applications": [
            "insulation plate", "wear plate", "slide surface",
            "low-friction pad", "electrical insulation",
        ],
    },
    "Ribs_and_Angle_Plates": {
        "aliases": [
            "rib plate", "angle plate", "stiffener plate",
            "gusset plate", "reinforcement plate", "webbed plate",
        ],
        "features": [
            "rib pattern", "plate thickness", "mounting holes",
            "welded edge", "right angle surface", "triangular gusset",
        ],
        "applications": [
            "structural reinforcement", "right-angle support", "weld stiffening",
            "frame gusset", "load bearing plate",
        ],
    },
    "Rods": {
        "aliases": [
            "solid rod", "guide rod", "support rod",
            "connecting rod", "steel rod", "precision rod",
        ],
        "features": [
            "rod diameter", "rod length", "threaded end",
            "ground surface", "stepped section", "chamfered end",
        ],
        "applications": [
            "linear guide", "structural support", "connecting linkage",
            "push rod mechanism", "shaft extension",
        ],
    },
    "Rollers": {
        "aliases": [
            "conveyor roller", "guide roller", "cam follower roller",
            "idler roller", "drive roller", "pressure roller",
        ],
        "features": [
            "roller diameter", "bearing bore", "roller surface",
            "shaft end", "journal bearing", "rubber coating",
        ],
        "applications": [
            "material conveying", "belt tracking", "cam following",
            "guide roller mechanism", "feed roller",
        ],
    },
    "Rotary_Shafts": {
        "aliases": [
            "rotary shaft", "precision shaft", "motor shaft",
            "drive shaft", "spindle shaft", "turned shaft",
        ],
        "features": [
            "shaft diameter", "keyway", "shoulder step",
            "thread end", "ground finish", "retaining ring groove",
        ],
        "applications": [
            "power transmission", "motor drive", "bearing support",
            "rotary mechanism", "spindle rotation",
        ],
    },
    "Sanitary_Vacuum_Tanks": {
        "aliases": [
            "sanitary tank", "vacuum chamber", "stainless steel tank",
            "process vessel", "pressure vessel", "hygienic tank",
        ],
        "features": [
            "tank shell", "dished head", "port connection",
            "sight glass", "drain valve", "pressure gauge port",
        ],
        "applications": [
            "food processing", "pharmaceutical vessel", "vacuum chamber",
            "chemical process tank", "sterile container",
        ],
    },
    "Screws": {
        "aliases": [
            "machine screw", "cap screw", "set screw",
            "socket head screw", "hex bolt screw", "shoulder screw",
        ],
        "features": [
            "head profile", "thread pitch", "shank diameter",
            "drive recess", "thread length", "point style",
        ],
        "applications": [
            "fastening", "assembly joining", "clamping force",
            "mechanical attachment", "precision fastening",
        ],
    },
    "Sensors": {
        "aliases": [
            "proximity sensor", "photoelectric sensor", "position sensor",
            "limit switch", "inductive sensor", "optical sensor",
        ],
        "features": [
            "sensing face", "cable connector", "housing body",
            "indicator LED", "mounting thread", "detection range",
        ],
        "applications": [
            "object detection", "position sensing", "limit detection",
            "automation sensing", "proximity detection",
        ],
    },
    "Set_Collars": {
        "aliases": [
            "shaft collar", "set collar", "locking collar",
            "clamping collar", "split collar", "solid collar",
        ],
        "features": [
            "bore diameter", "set screw", "split line",
            "collar width", "outer diameter", "clamping gap",
        ],
        "applications": [
            "shaft positioning", "axial stop", "component spacing",
            "bearing preload", "shaft locking",
        ],
    },
    "Shafts": {
        "aliases": [
            "linear shaft", "guide shaft", "support shaft",
            "precision shaft", "hardened shaft", "hollow shaft",
        ],
        "features": [
            "shaft diameter", "ground surface", "shaft length",
            "tolerance grade", "hardness zone", "end chamfer",
        ],
        "applications": [
            "linear motion guide", "bearing support", "bushing guide",
            "slide mechanism", "precision linear guide",
        ],
    },
    "Simplified_Adjustment_Units": {
        "aliases": [
            "adjustment unit", "fine adjustment stage", "positioning unit",
            "manual adjustment", "micrometer stage", "adjustment block",
        ],
        "features": [
            "adjustment screw", "slide platform", "guide rail",
            "lock mechanism", "graduation scale", "knob handle",
        ],
        "applications": [
            "fine positioning", "optical alignment", "sensor adjustment",
            "precision adjustment", "stage positioning",
        ],
    },
    "Slide_Rails": {
        "aliases": [
            "slide rail", "drawer slide", "linear slide rail",
            "telescopic rail", "ball slide", "extension rail",
        ],
        "features": [
            "rail profile", "ball cage", "stop mechanism",
            "mounting holes", "inner rail", "outer rail",
        ],
        "applications": [
            "drawer extension", "sliding mechanism", "keyboard tray slide",
            "equipment slide", "panel sliding",
        ],
    },
    "Slide_Screws": {
        "aliases": [
            "slide screw", "lead screw", "trapezoidal screw",
            "feed screw", "acme screw", "power screw",
        ],
        "features": [
            "thread form", "lead pitch", "screw shaft",
            "nut assembly", "anti-backlash nut", "end bearing",
        ],
        "applications": [
            "linear positioning", "manual feed", "table drive",
            "press mechanism", "jack screw lift",
        ],
    },
    "Springs": {
        "aliases": [
            "compression spring", "extension spring", "torsion spring",
            "coil spring", "die spring", "leaf spring",
        ],
        "features": [
            "coil diameter", "wire diameter", "free length",
            "spring rate", "active coils", "end type",
        ],
        "applications": [
            "force application", "shock absorption", "return mechanism",
            "die cushion", "spring-loaded mechanism",
        ],
    },
    "Sprockets_and_Chains": {
        "aliases": [
            "chain sprocket", "roller chain", "drive sprocket",
            "chain drive", "sprocket wheel", "timing sprocket",
        ],
        "features": [
            "tooth profile", "pitch diameter", "hub bore",
            "chain pitch", "roller diameter", "link plate",
        ],
        "applications": [
            "chain drive transmission", "conveyor drive", "power transmission",
            "bicycle chain mechanism", "industrial chain system",
        ],
    },
    "Stages": {
        "aliases": [
            "linear stage", "XY stage", "positioning stage",
            "precision stage", "manual stage", "motorized stage",
        ],
        "features": [
            "platform surface", "guide rail", "micrometer knob",
            "travel range", "cross roller", "mounting pattern",
        ],
        "applications": [
            "precision positioning", "microscope stage", "optical alignment",
            "wafer handling", "inspection stage",
        ],
    },
    "Timing_Pulleys": {
        "aliases": [
            "timing pulley", "toothed pulley", "synchronous pulley",
            "belt pulley", "drive pulley", "HTD pulley",
            "GT pulley", "idler pulley",
        ],
        "features": [
            "tooth profile", "pitch diameter", "bore hole",
            "flange ring", "hub width", "keyway slot",
            "set screw hole", "belt width groove",
        ],
        "applications": [
            "synchronous belt drive", "timing belt transmission", "precise rotation",
            "motor pulley drive", "conveyor belt drive",
        ],
    },
    "Urethanes": {
        "aliases": [
            "urethane part", "polyurethane component", "rubber bumper",
            "urethane pad", "elastomer element", "urethane roller",
        ],
        "features": [
            "durometer hardness", "elastic surface", "bonded metal insert",
            "compression pad", "custom shape", "molded profile",
        ],
        "applications": [
            "shock absorption", "vibration damping", "contact surface",
            "wear resistant pad", "buffer element",
        ],
    },
    "Washers": {
        "aliases": [
            "flat washer", "spring washer", "lock washer",
            "thrust washer", "wave washer", "Belleville washer",
        ],
        "features": [
            "inner diameter", "outer diameter", "washer thickness",
            "spring curvature", "serrated surface", "conical shape",
        ],
        "applications": [
            "load distribution", "bolt locking", "axial spacing",
            "vibration resistance", "surface protection",
        ],
    },
    # === Bearing subcategories (56-69) ===
    "bearing_H_ADAPTER": {
        "aliases": [
            "adapter sleeve bearing", "H-adapter bearing", "taper adapter",
            "bearing adapter sleeve", "withdrawal sleeve",
        ],
        "features": [
            "taper bore", "lock nut", "adapter sleeve",
            "split ring", "mounting thread", "tapered surface",
        ],
        "applications": [
            "bearing mounting on shaft", "tapered bore installation",
            "bearing adapter assembly", "shaft adapter fitting",
        ],
    },
    "bearing_SN\ud50c\ub7ec\uba38\ube14\ub85d": {
        "aliases": [
            "SN plummer block", "SN bearing housing", "split plummer block",
            "SN pedestal bearing", "SN series housing",
        ],
        "features": [
            "split housing", "cap bolts", "sealing groove",
            "oil hole", "base mounting", "locating ring",
        ],
        "applications": [
            "heavy shaft support", "split housing bearing",
            "industrial shaft mounting", "easy maintenance bearing",
        ],
    },
    "bearing_TAKEUP": {
        "aliases": [
            "take-up bearing", "take-up unit", "conveyor take-up",
            "tensioning bearing unit", "belt tensioner bearing",
        ],
        "features": [
            "sliding frame", "adjustment slots", "tensioning bolt",
            "bearing insert", "base rail", "adjustment range",
        ],
        "applications": [
            "conveyor belt tensioning", "chain tension adjustment",
            "belt take-up mechanism", "shaft position adjustment",
        ],
    },
    "bearing_UCF": {
        "aliases": [
            "UCF flanged bearing", "4-bolt flanged unit", "UCF bearing unit",
            "square flanged bearing", "flanged bearing housing",
        ],
        "features": [
            "square flange", "4 bolt holes", "bearing insert",
            "set screw", "grease fitting", "seal cover",
        ],
        "applications": [
            "flanged shaft support", "wall-mounted bearing",
            "vertical mounting bearing", "square flange mounting",
        ],
    },
    "bearing_UCFC": {
        "aliases": [
            "UCFC piloted flanged unit", "UCFC bearing", "round flanged bearing",
            "cartridge flanged unit", "pilot flange bearing",
        ],
        "features": [
            "round flange", "pilot diameter", "bolt circle",
            "bearing cartridge", "set screw", "inner ring",
        ],
        "applications": [
            "piloted flange mounting", "precision flange bearing",
            "centred flange support", "round cartridge bearing",
        ],
    },
    "bearing_UCFL": {
        "aliases": [
            "UCFL 2-bolt flanged unit", "UCFL bearing", "diamond flanged bearing",
            "oval flanged unit", "2-bolt flange bearing",
        ],
        "features": [
            "oval flange", "2 bolt holes", "bearing insert",
            "set screw", "grease port", "seal lip",
        ],
        "applications": [
            "2-bolt flange mounting", "light-duty shaft support",
            "diamond flange bearing", "space-saving flange mount",
        ],
    },
    "bearing_UCFS": {
        "aliases": [
            "UCFS flanged bearing", "UCFS unit", "flanged cartridge bearing",
            "UCFS bearing housing", "slide flange bearing",
        ],
        "features": [
            "flanged housing", "bearing insert", "set screw",
            "mounting bolt pattern", "seal arrangement", "grease point",
        ],
        "applications": [
            "flanged shaft support", "compact flange mount",
            "adjustable flange bearing", "industrial flange unit",
        ],
    },
    "bearing_UCP": {
        "aliases": [
            "UCP pillow block", "UCP bearing unit", "UCP pedestal bearing",
            "standard pillow block", "UCP series bearing",
        ],
        "features": [
            "pillow block housing", "bearing insert", "set screw",
            "base bolt holes", "grease fitting", "housing cap",
        ],
        "applications": [
            "horizontal shaft support", "standard pillow block mount",
            "conveyor shaft bearing", "general-purpose shaft support",
        ],
    },
    "bearing_UCT": {
        "aliases": [
            "UCT take-up unit", "UCT bearing", "UCT series take-up",
            "sliding take-up bearing", "UCT tensioner",
        ],
        "features": [
            "sliding frame", "take-up slot", "bearing insert",
            "adjustment bolt", "base rail", "set screw",
        ],
        "applications": [
            "belt tensioning", "chain take-up", "conveyor adjustment",
            "shaft position adjustment", "tension maintenance",
        ],
    },
    "bearing_UKFC": {
        "aliases": [
            "UKFC adapter flanged unit", "UKFC bearing", "adapter flange bearing",
            "taper bore flange unit", "UKFC series bearing",
        ],
        "features": [
            "round flange", "adapter sleeve", "lock nut",
            "taper bore", "bolt circle", "seal cover",
        ],
        "applications": [
            "adapter type flange mount", "taper bore flange bearing",
            "precision flange mounting", "adapter flange assembly",
        ],
    },
    "bearing_UKFL": {
        "aliases": [
            "UKFL adapter flanged unit", "UKFL bearing", "2-bolt adapter flanged",
            "oval adapter flange unit", "UKFL series bearing",
        ],
        "features": [
            "oval flange", "adapter sleeve", "lock nut",
            "2 bolt holes", "taper bore", "seal ring",
        ],
        "applications": [
            "adapter type 2-bolt mount", "light adapter flange bearing",
            "taper bore oval flange", "space-saving adapter mount",
        ],
    },
    "bearing_UKFS": {
        "aliases": [
            "UKFS adapter flanged unit", "UKFS bearing", "UKFS flanged cartridge",
            "adapter type flanged unit", "UKFS series bearing",
        ],
        "features": [
            "flanged housing", "adapter sleeve", "lock nut",
            "taper bore insert", "mounting bolts", "seal cover",
        ],
        "applications": [
            "adapter flanged shaft support", "UKFS series mounting",
            "taper bore cartridge bearing", "adapter flanged assembly",
        ],
    },
    "bearing_UKP": {
        "aliases": [
            "UKP adapter pillow block", "UKP bearing", "adapter pillow block",
            "taper bore pillow block", "UKP series bearing",
        ],
        "features": [
            "pillow block housing", "adapter sleeve", "lock nut",
            "taper bore", "base mounting holes", "grease fitting",
        ],
        "applications": [
            "adapter type shaft support", "taper bore pillow block",
            "heavy-duty adapter bearing", "UKP shaft mounting",
        ],
    },
    "bearing_UKT": {
        "aliases": [
            "UKT adapter take-up", "UKT bearing", "adapter take-up unit",
            "taper bore take-up", "UKT series bearing",
        ],
        "features": [
            "sliding frame", "adapter sleeve", "lock nut",
            "take-up slot", "taper bore", "adjustment bolt",
        ],
        "applications": [
            "adapter type take-up", "taper bore tensioning",
            "conveyor adapter take-up", "adapter tension adjustment",
        ],
    },
    # === Extended automotive/new categories (72-84) ===
    "Wheels": {
        "aliases": [
            "wheel assembly", "drive wheel", "machine wheel",
            "caster wheel", "hand wheel", "flywheel",
        ],
        "features": [
            "hub bore", "spoke pattern", "rim profile",
            "bolt circle", "wheel diameter", "tire seat",
        ],
        "applications": [
            "vehicle wheel", "manual operation", "energy storage flywheel",
            "transport wheel", "material handling wheel",
        ],
    },
    "Tires": {
        "aliases": [
            "rubber tire", "pneumatic tire", "solid tire",
            "industrial tire", "wheel tire", "traction tire",
        ],
        "features": [
            "tread pattern", "sidewall", "bead seat",
            "tire width", "aspect ratio", "rim diameter",
        ],
        "applications": [
            "vehicle traction", "load bearing", "shock absorption",
            "material handling vehicle", "industrial cart tire",
        ],
    },
    "Suspension": {
        "aliases": [
            "suspension system", "shock absorber", "suspension arm",
            "spring strut", "suspension linkage", "damper assembly",
        ],
        "features": [
            "damper body", "spring coil", "mounting eye",
            "ball joint", "bushing mount", "control arm",
        ],
        "applications": [
            "vehicle suspension", "vibration damping", "ride comfort",
            "load suspension", "chassis support",
        ],
    },
    "Brakes": {
        "aliases": [
            "brake assembly", "disc brake", "brake caliper",
            "brake pad", "drum brake", "brake mechanism",
        ],
        "features": [
            "brake disc", "caliper body", "brake pad",
            "piston bore", "mounting bracket", "rotor surface",
        ],
        "applications": [
            "vehicle braking", "motion stopping", "speed control",
            "safety brake", "machine brake",
        ],
    },
    "Powertrain": {
        "aliases": [
            "powertrain component", "drivetrain part", "transmission element",
            "drive mechanism", "engine component", "power delivery",
        ],
        "features": [
            "gear mesh", "shaft connection", "housing bore",
            "bearing seat", "oil passage", "seal groove",
        ],
        "applications": [
            "power transmission", "torque delivery", "speed conversion",
            "vehicle drivetrain", "engine-to-wheel power",
        ],
    },
    "Clutches": {
        "aliases": [
            "clutch assembly", "friction clutch", "electromagnetic clutch",
            "one-way clutch", "disc clutch", "clutch mechanism",
        ],
        "features": [
            "friction disc", "pressure plate", "release bearing",
            "spline hub", "clutch housing", "diaphragm spring",
        ],
        "applications": [
            "power engagement", "torque coupling", "speed matching",
            "machine start-stop", "selective drive connection",
        ],
    },
    "Pistons": {
        "aliases": [
            "piston assembly", "engine piston", "hydraulic piston",
            "reciprocating piston", "piston head", "cylinder piston",
        ],
        "features": [
            "piston crown", "ring groove", "wrist pin bore",
            "skirt profile", "compression ring", "oil ring",
        ],
        "applications": [
            "reciprocating engine", "hydraulic cylinder", "compressor",
            "pneumatic actuator", "internal combustion engine",
        ],
    },
    "Differential": {
        "aliases": [
            "differential gear", "differential assembly", "diff unit",
            "bevel gear set", "ring and pinion", "differential carrier",
        ],
        "features": [
            "ring gear", "pinion gear", "spider gear",
            "carrier housing", "side gear", "bearing cap",
        ],
        "applications": [
            "vehicle differential", "speed differential", "torque splitting",
            "axle drive", "cornering mechanism",
        ],
    },
    "Turbocharger": {
        "aliases": [
            "turbocharger assembly", "turbo unit", "exhaust turbine",
            "compressor housing", "turbo impeller", "forced induction",
        ],
        "features": [
            "turbine wheel", "compressor wheel", "center housing",
            "wastegate", "bearing journal", "oil inlet",
        ],
        "applications": [
            "engine boosting", "forced induction", "exhaust energy recovery",
            "air compression", "performance enhancement",
        ],
    },
    "Bolts_and_Nuts": {
        "aliases": [
            "bolt and nut", "hex bolt", "hex nut",
            "stud bolt", "flange bolt", "cap nut",
            "coupling nut", "lock nut",
        ],
        "features": [
            "hex head", "thread pitch", "shank length",
            "nut height", "flange face", "washer face",
        ],
        "applications": [
            "structural fastening", "mechanical joint", "assembly connection",
            "tension fastening", "bolt-nut clamping",
        ],
    },
    "Flanges": {
        "aliases": [
            "pipe flange", "weld neck flange", "slip-on flange",
            "blind flange", "lap joint flange", "socket weld flange",
        ],
        "features": [
            "bolt circle", "raised face", "gasket surface",
            "bore diameter", "flange thickness", "hub taper",
        ],
        "applications": [
            "pipe connection", "pressure vessel", "duct flange joint",
            "piping system connection", "equipment flange",
        ],
    },
    "Housing": {
        "aliases": [
            "bearing housing", "motor housing", "gear housing",
            "enclosure housing", "protective housing", "cast housing",
        ],
        "features": [
            "bore seat", "mounting face", "cover seal",
            "oil drain", "inspection port", "ribbed wall",
        ],
        "applications": [
            "component enclosure", "bearing protection", "gear enclosure",
            "motor casing", "transmission housing",
        ],
    },
    "Airbag_Module": {
        "aliases": [
            "airbag unit", "safety airbag", "inflator module",
            "restraint system module", "SRS module", "airbag assembly",
        ],
        "features": [
            "inflator body", "airbag cushion", "mounting bracket",
            "electrical connector", "deployment mechanism", "cover plate",
        ],
        "applications": [
            "vehicle safety", "occupant protection", "crash restraint",
            "steering wheel airbag", "side curtain airbag",
        ],
    },
}


def get_categories():
    """학습에 사용된 81개 카테고리 목록 반환"""
    return sorted(CATEGORY_DETAILS.keys())


def get_aliases(category):
    """카테고리의 별칭 목록 반환"""
    info = CATEGORY_DETAILS.get(category, {})
    return info.get("aliases", [category.replace("_", " ").lower()])


def get_features(category):
    """카테고리의 형상/특징 목록 반환"""
    info = CATEGORY_DETAILS.get(category, {})
    return info.get("features", ["detailed dimensions"])


def get_applications(category):
    """카테고리의 용도 목록 반환"""
    info = CATEGORY_DETAILS.get(category, {})
    return info.get("applications", ["general machinery"])
