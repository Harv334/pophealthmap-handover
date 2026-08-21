"""Data export: the figure checkboxes have to be visible, and Download reachable.

This panel exists to tick figures, and twice it has shipped with nothing to
tick. First the eight groups all rendered collapsed, because cbOpenGroups
starts empty and the render read `cbOpenGroups[g] || false`, so the pane opened
on eight headings and a "No figures chosen" line. Then, with the groups open,
`.cb-cols` was a flex item that could shrink below its content and settled at
92 pixels holding 4,400 of checkboxes.

Both looked identical from the outside: a panel that appears finished and
empty. Neither showed up as an error, and the DOM was correct in both cases, so
the only thing that catches it is measuring what is actually on the screen.

Run against a served copy:  python -m http.server 8902
"""
import sys
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8902/index.html"
SETTLE = int(sys.argv[2]) if len(sys.argv) > 2 else 12

# The list starts above the fold at every one of these. It is cut off mid-row
# on the shorter two, which is the scroll affordance doing its job; what must
# not happen is the list beginning below the fold, where the panel reads as
# empty rather than as scrollable.
VIEWPORTS = [(1500, 1000), (1366, 768), (1280, 720)]

fails = []


def check(name, ok, detail=""):
    print(("  PASS  " if ok else "  FAIL  ") + name + (f"   {detail}" if detail else ""))
    if not ok:
        fails.append(name)


def driver(w, h):
    o = Options()
    o.add_argument("--headless=new")
    o.add_argument("--disable-gpu")
    o.add_argument(f"--window-size={w},{h}")
    o.set_capability("goog:loggingPrefs", {"browser": "ALL"})
    return webdriver.Chrome(options=o)


for w, h in VIEWPORTS:
    d = driver(w, h)
    try:
        d.get(URL)
        time.sleep(SETTLE)
        d.execute_script(
            """document.querySelector('.mode-rail .mode-btn[data-mode="csv"]').click();""")
        time.sleep(3)

        m = d.execute_script("""
          var box  = document.getElementById('cb-cols');
          var pane = document.getElementById('tab-csv');
          var rows = [...box.querySelectorAll('.cb-col')].filter(function (e) {
            var b = e.getBoundingClientRect();
            return b.top >= 0 && b.bottom <= window.innerHeight;
          });
          var btn = document.getElementById('cb-download').getBoundingClientRect();
          return {
            boxes: box.querySelectorAll('input[type=checkbox]').length,
            openGroups: document.querySelectorAll('#cb-cols .cb-grp-hd.open').length,
            groups: document.querySelectorAll('#cb-cols .cb-grp-hd').length,
            visibleRows: rows.length,
            paneScrolls: pane.scrollHeight > pane.clientHeight + 4,
            btnTop: Math.round(btn.top), btnBottom: Math.round(btn.bottom),
            vh: window.innerHeight,
          };
        """)
        print(f"\n  {w}x{h}")
        check("every figure group opens by default",
              m["groups"] > 0 and m["openGroups"] == m["groups"],
              f"{m['openGroups']} of {m['groups']}")
        check("the panel offers its full set of figures", m["boxes"] > 100, str(m["boxes"]))
        check("checkboxes start above the fold, so the list reads as scrollable",
              m["visibleRows"] >= 2, f"{m['visibleRows']} rows on screen")
        check("and the pane scrolls to reach the rest", m["paneScrolls"])
        # Sticky, so it does not sit four thousand pixels below the list.
        check("Download CSV stays on screen",
              0 < m["btnTop"] and m["btnBottom"] <= m["vh"] + 1,
              f"y={m['btnTop']}-{m['btnBottom']} of {m['vh']}")

        # Ticking has to register, and collapsing has to still work.
        d.execute_script("document.querySelector('#cb-cols input[type=checkbox]').click();")
        time.sleep(1.2)
        check("ticking one counts it",
              "1 figure chosen" in d.execute_script(
                  "return document.getElementById('cb-picked').textContent;"),
              d.execute_script(
                  "return document.getElementById('cb-picked').textContent.trim();")[:50])
        d.execute_script("document.querySelector('#cb-cols .cb-grp-hd').click();")
        time.sleep(1.2)
        check("a group still collapses by hand",
              d.execute_script(
                  "return document.querySelectorAll('#cb-cols .cb-grp-hd.open').length;")
              == m["groups"] - 1)

        sev = [e for e in d.get_log("browser")
               if e["level"] == "SEVERE" and "favicon" not in e["message"]]
        check("no severe console errors", not sev,
              "; ".join(e["message"][:120] for e in sev[:2]))
    finally:
        d.quit()

print()
print(("FAILED: " + "; ".join(fails)) if fails else "all checks passed")
sys.exit(1 if fails else 0)
