#!/bin/sh
# docs/TODO.md → docs/todo.pdf (A4): pandoc to HTML, Chrome headless prints it. Run on the Mac: scripts/todo_pdf.sh
set -e
cd "$(dirname "$0")/.."
TMP=$(mktemp -d)
cat > "$TMP/style.css" <<'CSS'
@page { size: A4; margin: 14mm 14mm 16mm; }
body { font: 10pt/1.4 -apple-system, "Helvetica Neue", Arial, sans-serif; color: #1f2328; max-width: none; margin: 0; }
h1 { font-size: 20pt; margin: 0 0 4pt; }
h2 { font-size: 13pt; margin: 14pt 0 4pt; padding-bottom: 2pt; border-bottom: 1px solid #d0d7de; break-after: avoid; }
p { margin: 3pt 0; }
ul { padding-left: 16pt; margin: 3pt 0; }
li { margin: 2.5pt 0; break-inside: avoid; }
li input[type=checkbox] { margin-right: 4pt; }
code { font: 8.5pt Menlo, monospace; background: #f3f4f6; padding: 0 2pt; border-radius: 2pt; }
hr { border: 0; border-top: 1px solid #d0d7de; }
CSS
pandoc docs/TODO.md -f gfm -t html5 -s --css "$TMP/style.css" -o "$TMP/todo.html" \
  --variable pagetitle="Bump'em to do"
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="$PWD/docs/todo.pdf" "file://$TMP/todo.html" 2>/dev/null
rm -r "$TMP"
echo docs/todo.pdf
