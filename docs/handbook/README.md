# Handbook (LaTeX)

`main.tex` + `sections/*.tex` + `figures/` → PDF for future students: hardware review (Stanford / thesis / built), parts bought, cabling maps, software from firmware to UI, procedures, faults found.

**Overleaf:** upload `bumpem-handbook-overleaf.zip` (New Project → Upload Project). Compiler pdfLaTeX, main document `main.tex`.
**Local:** `pdflatex main.tex` twice (standard packages only, works with BasicTeX).
Rebuild the zip after editing: `zip -r bumpem-handbook-overleaf.zip main.tex sections figures`.

Facts come from `docs/knowledge/`, `docs/STATUS.md`, `escon/README.md`, `hardware/*/README.md`, `docs/API.md`, `docs/PROTOCOL.md`. When those change, update the matching section here. Yellow "TO FILL IN" boxes mark facts not in the repo.
