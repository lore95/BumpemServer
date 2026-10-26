"""Parts, pads, tracks and vias of the board as JSON, for soldering_guide.py. Needs KiCad's Python (pcbnew):
$KPY dump_board.py bumpem-carrier.kicad_pcb fab/board.json   (KPY: see build.sh)"""
import json, sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
mm = pcbnew.ToMM
segs = []
for t in b.GetTracks():
    if t.GetClass() == "PCB_TRACK":
        segs.append(dict(layer=b.GetLayerName(t.GetLayer()), net=t.GetNetname(), a=[mm(t.GetStart().x), mm(t.GetStart().y)], b=[mm(t.GetEnd().x), mm(t.GetEnd().y)], w=mm(t.GetWidth())))
    elif t.GetClass() == "PCB_VIA":
        segs.append(dict(layer="via", net=t.GetNetname(), a=[mm(t.GetPosition().x), mm(t.GetPosition().y)], d=mm(t.GetWidth())))
fps = []
for f in b.GetFootprints():
    bb = f.GetBoundingBox(False, False)
    pads = [dict(num=p.GetNumber(), net=p.GetNetname(), x=mm(p.GetPosition().x), y=mm(p.GetPosition().y),
                 sx=mm(p.GetSize().x), sy=mm(p.GetSize().y), drill=mm(p.GetDrillSize().x)) for p in f.Pads()]
    fps.append(dict(ref=f.GetReference(), value=f.GetValue(), x=mm(f.GetPosition().x), y=mm(f.GetPosition().y), rot=f.GetOrientationDegrees(),
                    bbox=[mm(bb.GetX()), mm(bb.GetY()), mm(bb.GetWidth()), mm(bb.GetHeight())], pads=pads))
json.dump(dict(segs=segs, fps=fps), open(sys.argv[2], "w"), indent=0)
print(len(segs), len(fps))
