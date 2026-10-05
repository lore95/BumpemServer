"""Single source of truth for the carrier board's parts and connections (used by gen_schematic.py and checked by gen_carrier.py).

Pin names: Teensy 4.1 pads 1-24 = one long edge (GND, 0-12, 3V3, 24-32), pads 25-48 = the other edge (33-41, GND, 13-23, 3V3, GND, VIN),
same numbering as XenGi/teensy_library. MCP4728 breakout (Adafruit 4470): pads 1-6 = VCC GND SCL SDA LDAC RDY, 7-12 = GND VA VB VC VD VCC.
"""
import uuid

MODS = "ABCD"
T_FIRST = ["GND"] + [str(i) for i in range(13)] + ["3V3"] + [str(i) for i in range(24, 33)]                        # pads 1..24
T_SECOND = [str(i) for i in range(33, 42)] + ["GND"] + [str(i) for i in range(13, 24)] + ["3V3", "GND", "VIN"]     # pads 25..48
TEENSY_PINS = {str(n + 1): name for n, name in enumerate(T_FIRST + T_SECOND)}
DAC_PINS = {str(i + 1): n for i, n in enumerate(["VCC", "GND", "SCL", "SDA", "LDAC", "RDY", "GND", "VA", "VB", "VC", "VD", "VCC"])}

# Teensy pin name -> net (firmware/src/main.ino: enable 27-30, force A0-A3 = 14-17, I2C 18/19)
TEENSY_NET = {"19": "SCL", "18": "SDA", "14": "F_A", "15": "F_B", "16": "F_C", "17": "F_D",
              "27": "EN_A", "28": "EN_B", "29": "EN_C", "30": "EN_D"}

def _teensy_nets():
    nets = {}
    for pad, name in TEENSY_PINS.items():
        if name in TEENSY_NET:
            nets[pad] = TEENSY_NET[name]
    nets["1"] = "GND"; nets["34"] = "GND"; nets["47"] = "GND"      # GND pads used (pad 1 and the two on the other edge)
    nets["15"] = "+3V3"                                              # 3V3 pad on the GND/0-12 edge; pad 46 (other 3V3) not used
    return nets                                                      # VIN (pad 48) never connected

PARTS = {
    "U1": ("bumpem-carrier:Teensy41_Socket", "Teensy 4.1", "bumpem-carrier:Teensy41_Socket", _teensy_nets()),
    "U2": ("bumpem-carrier:MCP4728_Breakout", "MCP4728 (Adafruit 4470)", "bumpem-carrier:Adafruit_MCP4728_Socket",
           {"2": "GND", "3": "SCL", "4": "SDA", "7": "GND", "8": "SP_A", "9": "SP_B", "10": "SP_C", "11": "SP_D", "12": "+3V3"}),
}
for k, m in enumerate(MODS):
    PARTS[f"J{k + 1}"] = ("Connector:Screw_Terminal_01x05", f"Module {m}",
                          "Connector_Phoenix_MSTB:PhoenixContact_MSTB_2,5_5-GF-5,08_1x05_P5.08mm_Horizontal_ThreadedFlange",
                          {"1": f"EN_{m}", "2": f"SP_{m}", "3": "GND", "4": "GND", "5": f"FIN_{m}"})
    PARTS[f"R{k + 1}"] = ("Device:R", "1k", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
                          {"1": f"F_{m}", "2": f"FIN_{m}"})
    PARTS[f"R{k + 5}"] = ("Device:R", "1M", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
                          {"1": f"F_{m}", "2": "GND"})
    PARTS[f"D{k + 1}"] = ("Device:D_Schottky", "BAT85", "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal",
                          {"1": "+3V3", "2": f"F_{m}"})
for i in range(4):
    PARTS[f"H{i + 1}"] = ("Mechanical:MountingHole", "M3", "MountingHole:MountingHole_3.2mm_M3", {})

NS = uuid.UUID("6f1c7c52-1d0e-4b8e-9a51-0b5d2c7e1a00")
def sym_uuid(ref):
    """Stable symbol UUID, shared by the schematic symbol and the PCB footprint path."""
    return str(uuid.uuid5(NS, ref))
