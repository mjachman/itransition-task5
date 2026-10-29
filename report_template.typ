#set page(paper: "us-letter", margin: (x: 28pt, top: 16pt, bottom: 16pt))
#set text(font: "Arial", size: 7pt)

#let d = json("data.json")

// Header: Corporate Identity & Report Metadata
#grid(
  columns: (1fr, auto),
  [
    #text(13pt, weight: "bold", fill: rgb("#0f172a"))[WEYLAND-YUTANI CORPORATION] \
    #text(7pt, weight: "bold", fill: rgb("#0284c7"))[RESOURCE EXTRACTION & STATISTICAL ANALYSIS REPORT]
  ],
  [
    #align(right)[
      #text(8pt, weight: "bold", fill: rgb("#0f172a"))[DAILY PRODUCTION AUDIT]
    ]
  ],
)

#v(3pt)

// Metadata Ribbon
#rect(width: 100%, fill: rgb("#f8fafc"), stroke: 0.4pt + rgb("#cbd5e1"), radius: 2pt, inset: 3.5pt)[
  #grid(
    columns: (1fr, 1.6fr, 0.8fr),
    [
      #text(5pt, weight: "bold", fill: rgb("#64748b"))[OBSERVATION TIMELINE] \
      #text(6.5pt, weight: "bold", fill: rgb("#0f172a"))[#d.meta.timeline]
    ],
    [
      #text(5pt, weight: "bold", fill: rgb("#64748b"))[ACTIVE DETECTION CRITERIA] \
      #text(5.5pt, weight: "bold", fill: rgb("#0f172a"))[#d.meta.criteria]
    ],
    [
      #text(5pt, weight: "bold", fill: rgb("#64748b"))[MEASUREMENT UNIT] \
      #text(6.5pt, weight: "bold", fill: rgb("#0f172a"))[Metric Tons [t]]
    ],
  )
]

#v(2pt)

// Section 01: Summary Statistics
#text(8pt, weight: "bold")[#text(fill: rgb("#0284c7"))[01.] STATISTICAL SUMMARY] \
#text(5.5pt, style: "italic", fill: rgb("#64748b"))[Table 1: Daily extraction metrics per mine and total output (ddof = 1).]
#v(1pt)
#table(
  columns: (1.6fr, 1fr, 1fr, 1fr, 1fr),
  stroke: 0.3pt + rgb("#cbd5e1"),
  fill: (col, row) => if row == 0 { rgb("#0f172a") } else if row == d.stats.len() { rgb("#f1f5f9") } else if calc.even(row) { rgb("#f8fafc") } else { none },
  align: (col, row) => if col == 0 { left } else { right },
  inset: if d.stats.len() > 8 { 1.3pt } else { 2.2pt },
  table.header(
    [*#text(fill: white, size: 6pt)[MINE]*],
    [*#text(fill: white, size: 6pt)[MEAN]*],
    [*#text(fill: white, size: 6pt)[STD DEV]*],
    [*#text(fill: white, size: 6pt)[MEDIAN]*],
    [*#text(fill: white, size: 6pt)[IQR]*],
  ),
  ..d.stats.map(s => (
    if s.is_total [ *#text(fill: rgb("#0f172a"))[#s.mine]* ] else [ #s.mine ],
    if s.is_total [ *#s.mean* ] else [ #s.mean ],
    if s.is_total [ *#s.std* ] else [ #s.std ],
    if s.is_total [ *#s.median* ] else [ #s.median ],
    if s.is_total [ *#s.iqr* ] else [ #s.iqr ],
  )).flatten()
)

#v(2pt)

// Section 02: Visual Trends
#text(8pt, weight: "bold")[#text(fill: rgb("#0284c7"))[02.] PRODUCTION CHART & TRENDS (#d.meta.short_timeline)]
#v(1pt)
#rect(width: 100%, stroke: 0.3pt + rgb("#cbd5e1"), inset: 0pt, radius: 2pt)[
  #image("chart.png", width: 100%)
]
#v(1pt)
#text(5.5pt, style: "italic", fill: rgb("#64748b"))[Figure 1: Daily extraction data from #d.meta.timeline across active mines with fitted polynomial regression and outlier highlighting.]

#v(2pt)

#pagebreak()
// Section 03: Operational Anomaly Audit (Separate Sections for Spikes and Drops)
#text(8pt, weight: "bold")[#text(fill: rgb("#0284c7"))[03.] DETECTED ANOMALIES] \
#text(5.5pt, style: "italic", fill: rgb("#64748b"))[#d.meta.threshold_sub]
#v(1.5pt)

#grid(
  columns: (1fr, 1fr),
  gutter: 6pt,
  [
    #text(7pt, weight: "bold", fill: rgb("#b91c1c"))[3.1 Production Spikes] \
    #text(5pt, style: "italic", fill: rgb("#64748b"))[Table 2: Significant bursts exceeding mine baselines.]
    #v(1pt)
    #if d.spikes.len() > 0 [
      #table(
        columns: (42pt, 54pt, 36pt, 48pt, 1fr),
        stroke: 0.3pt + rgb("#cbd5e1"),
        fill: (col, row) => if row == 0 { rgb("#b91c1c") } else if calc.even(row) { rgb("#fef2f2") } else { none },
        align: (col, row) => if col == 0 { center } else if col in (2, 3) { right } else { left },
        inset: 2pt,
        table.header(
          [*#text(fill: white, size: 5pt)[DATE]*],
          [*#text(fill: white, size: 5pt)[MINE]*],
          [*#text(fill: white, size: 5pt)[RECORDED]*],
          [*#text(fill: white, size: 5pt)[DEVIATION]*],
          [*#text(fill: white, size: 5pt)[TEST]*],
        ),
        ..d.spikes.map(a => (
          [ #text(size: 5.5pt)[#a.date] ],
          [ #text(size: 5.5pt, weight: "bold")[#a.mine] ],
          [ #text(size: 5.5pt)[#a.val] ],
          [ #text(size: 5.5pt, weight: "bold", fill: rgb("#b91c1c"))[#a.variance] ],
          [ #text(size: 5pt)[#a.detected_by] ],
        )).flatten()
      )
    ] else [
      #rect(width: 100%, fill: rgb("#f8fafc"), stroke: 0.3pt + rgb("#e2e8f0"), inset: 6pt, radius: 2pt)[
        #text(5.5pt, style: "italic", fill: rgb("#64748b"))[No positive extraction spikes detected under current thresholds.]
      ]
    ]
  ],
  [
    #text(7pt, weight: "bold", fill: rgb("#1d4ed8"))[3.2 Production Drops] \
    #text(5pt, style: "italic", fill: rgb("#64748b"))[Table 3: Production shortfalls falling below baseline.]
    #v(1pt)
    #if d.drops.len() > 0 [
      #table(
        columns: (42pt, 54pt, 36pt, 48pt, 1fr),
        stroke: 0.3pt + rgb("#cbd5e1"),
        fill: (col, row) => if row == 0 { rgb("#1d4ed8") } else if calc.even(row) { rgb("#eff6ff") } else { none },
        align: (col, row) => if col == 0 { center } else if col in (2, 3) { right } else { left },
        inset: 2pt,
        table.header(
          [*#text(fill: white, size: 5pt)[DATE]*],
          [*#text(fill: white, size: 5pt)[MINE]*],
          [*#text(fill: white, size: 5pt)[RECORDED]*],
          [*#text(fill: white, size: 5pt)[DEVIATION]*],
          [*#text(fill: white, size: 5pt)[TEST]*],
        ),
        ..d.drops.map(a => (
          [ #text(size: 5.5pt)[#a.date] ],
          [ #text(size: 5.5pt, weight: "bold")[#a.mine] ],
          [ #text(size: 5.5pt)[#a.val] ],
          [ #text(size: 5.5pt, weight: "bold", fill: rgb("#1d4ed8"))[#a.variance] ],
          [ #text(size: 5pt)[#a.detected_by] ],
        )).flatten()
      )
    ] else [
      #rect(width: 100%, fill: rgb("#f8fafc"), stroke: 0.3pt + rgb("#e2e8f0"), inset: 6pt, radius: 2pt)[
        #text(5.5pt, style: "italic", fill: rgb("#64748b"))[No operational production drops detected under current thresholds.]
      ]
    ]
  ],
)

#pagebreak()

// Page 2: Appendix Ledger (Adaptive Layout for N Mines)
#text(8pt, weight: "bold")[#text(fill: rgb("#0284c7"))[04.] DAILY EXTRACTION LEDGER] \
#text(5.5pt, style: "italic", fill: rgb("#64748b"))[Table 4: High-resolution daily output ledger across mines with highlighted algorithmic outliers (Red: Spikes, Blue: Drops).]
#v(2pt)

#let make_subtable(rows) = table(
  columns: (40pt, ) + (1fr, ) * d.ledger.num_cols,
  stroke: 0.25pt + rgb("#cbd5e1"),
  fill: (col, row) => if row == 0 { rgb("#0f172a") } else if calc.even(row) { rgb("#f8fafc") } else { none },
  align: (col, row) => if col == 0 { center } else { right },
  inset: 1.5pt,
  table.header(..d.ledger.headers.map(h => [*#text(fill: white, size: 5pt)[#h]*])),
  ..rows.map(r => r.map(c => (
    if c.kind == "SPIKE" [ #text(fill: rgb("#b91c1c"), weight: "bold")[#c.text\*] ]
    else if c.kind == "DROP" [ #text(fill: rgb("#1d4ed8"), weight: "bold")[#c.text\*] ]
    else [ #c.text ]
  ))).flatten().flatten()
)

#if d.ledger.is_wide [
  #let num = d.ledger.num_cols
  #let col_w = (556pt - 36pt) / num
  #table(
    columns: (36pt, ) + (col_w, ) * num,
    stroke: 0.2pt + rgb("#cbd5e1"),
    fill: (col, row) => if row == 0 { rgb("#0f172a") } else if calc.even(row) { rgb("#f8fafc") } else { none },
    align: (col, row) => if col == 0 { center } else { right },
    inset: 1.2pt,
    table.header(..d.ledger.headers.map(h => [*#text(fill: white, size: 4.5pt)[#h]*])),
    ..d.ledger.full_rows.map(r => r.map(c => (
      if c.kind == "SPIKE" [ #text(fill: rgb("#b91c1c"), weight: "bold", size: 4.5pt)[#c.text\*] ]
      else if c.kind == "DROP" [ #text(fill: rgb("#1d4ed8"), weight: "bold", size: 4.5pt)[#c.text\*] ]
      else [ #text(size: 4.5pt)[#c.text] ]
    ))).flatten().flatten()
  )
] else [
  #grid(
    columns: (1fr, 1fr),
    gutter: 4pt,
    make_subtable(d.ledger.left_rows),
    make_subtable(d.ledger.right_rows),
  )
]

#v(3pt)
#rect(width: 100%, fill: rgb("#f8fafc"), stroke: 0.3pt + rgb("#cbd5e1"), inset: 3pt, radius: 2pt)[
  #text(5pt, fill: rgb("#64748b"))[\* Methodological Note: Highlighted cell values denote algorithmic anomalies detected across parametric baselines. Positive surges (Red) and operational deficits (Blue) are benchmarked against rolling averages and distribution thresholds. All values expressed in Metric Tons [t].]
]
