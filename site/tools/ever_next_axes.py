"""EVER NEXT axes: the ground-up dimensions every improvement item is composed from.

SURFACES  everything in this repository, each with one KIND and optional TRAITS:
          kinds   page · ui · datapanel · layout · image · texture · runtime · tool · doc
          traits  interactive (can be operated) · motion (animates) · data (shows values) · live (updates from markets)
ASPECTS   qualities to refine. An aspect applies to a surface when the surface's kind is in `kinds` and, if the aspect
          names `traits`, the surface has one of them; `include` adds named surfaces, `exclude` removes them.
          Moves are written with the surface as their object (never its subject), so every sentence stays grammatical.
          A move may carry a condition in brackets, e.g. "f[data]:", and then applies only to surfaces whose kind,
          traits or id match one of the listed words. Each move is tagged by its nature, which chooses the depth text:
            a: an audit (look and record)    f: a fix (change something)       w: writing (change words)
            t: a test (write a QA check)     h: human judgement (a person must look)
DEPTHS    five stages per move nature: the same move always has a better next version.
"""

LAYERS = ["SITE PAGES", "SITE COMPONENTS", "DESK", "ASSETS", "SYSTEMS"]
KINDS = {"page", "ui", "datapanel", "layout", "image", "texture", "runtime", "tool", "doc"}
TRAITS = {"interactive", "motion", "data", "live"}

SURFACES = [
    # id, name, layer, kind, traits
    ("home", "the Home page", 0, "page", "interactive"),
    ("hub", "the Desks hub", 0, "page", "interactive"),
    ("learn", "the Learn page", 0, "page", "interactive"),
    ("how", "the How it works page", 0, "page", ""),
    ("identity", "the QuadCOM page", 0, "page", ""),
    ("datapage", "the Data page", 0, "page", "data"),
    ("glossary", "the Glossary page", 0, "page", "interactive"),
    ("catalogpage", "the Catalog page", 0, "page", "interactive"),
    ("evernext", "the EVER NEXT page", 0, "page", "interactive data"),
    ("notfound", "the 404 page", 0, "page", "interactive"),
    ("offline", "the offline page", 0, "page", "interactive"),
    ("header", "the site header and primary nav", 1, "ui", "interactive"),
    ("tabbar", "the phone tab bar", 1, "ui", "interactive"),
    ("orb", "the raised DESK orb", 1, "ui", "interactive"),
    ("more", "the MORE sheet", 1, "ui", "interactive motion"),
    ("toast", "the toast system", 1, "ui", "motion"),
    ("search", "the search fields", 1, "ui", "interactive"),
    ("segment", "the segmented skin control", 1, "ui", "interactive"),
    ("termsheet", "the glossary term sheet", 1, "ui", "interactive motion"),
    ("pager", "the page-to-page pager", 1, "ui", "interactive"),
    ("footer", "the footer", 1, "ui", "interactive"),
    ("progress", "the reading-progress strip", 1, "ui", "motion"),
    ("totop", "the back-to-top control", 1, "ui", "interactive"),
    ("chips", "the coin chips", 1, "ui", "interactive"),
    ("deskcards", "the desk cards", 1, "ui", "interactive"),
    ("panel", "the content panel", 1, "ui", ""),
    ("metricrow", "the metric rows", 1, "ui", "data"),
    ("provtag", "the provenance tags", 1, "ui", "data"),
    ("anchors", "the section anchor links", 1, "ui", "interactive"),
    ("azindex", "the A–Z index", 1, "ui", "interactive"),
    ("catfilter", "the catalog filters", 1, "ui", "interactive"),
    ("storagecard", "the device storage card", 1, "ui", "data"),
    ("cmdbar", "the desk command bar and brand", 2, "ui", "interactive motion"),
    ("quote", "the headline price quote", 2, "datapanel", "data live"),
    ("chart", "the tape and price chart", 2, "datapanel", "data live motion"),
    ("axis", "the chart axis labels", 2, "datapanel", "data live"),
    ("fleetbal", "the fleet balance cell", 2, "datapanel", "data live"),
    ("bullbear", "the bull / bear balance", 2, "datapanel", "data live"),
    ("toppico", "the Top PicoProcessor panel", 2, "datapanel", "data live"),
    ("fundcells", "the fund cells", 2, "datapanel", "data live"),
    ("singular", "the Best Singular Trade", 2, "datapanel", "data live"),
    ("micro", "the microstructure panel", 2, "datapanel", "data live"),
    ("loss", "the loss control panel", 2, "datapanel", "data live"),
    ("leader", "the leaderboard", 2, "datapanel", "data live"),
    ("wall", "the processor wall", 2, "datapanel", "data live motion"),
    ("book", "the order book", 2, "datapanel", "data live"),
    ("horizons", "the horizon rail", 2, "datapanel", "data live"),
    ("vision", "the VISION view", 2, "datapanel", "data live motion"),
    ("glimmersheet", "the GLIMMER sheet", 2, "ui", "interactive data"),
    ("deskbar", "the portrait desk bar", 2, "ui", "interactive"),
    ("deskland", "the landscape desk layout", 2, "layout", ""),
    ("deskport", "the portrait desk layout", 2, "layout", ""),
    ("coins", "the coin marks", 3, "image", ""),
    ("logo", "the official logo files", 3, "image", ""),
    ("seal", "the Genesis Seal", 3, "texture", ""),
    ("intaglio", "the intaglio field", 3, "texture", ""),
    ("corners", "the quarter-diamond corners", 3, "texture", ""),
    ("band", "the guilloche band", 3, "texture", ""),
    ("bezel", "the reeded bezel", 3, "texture", ""),
    ("icons", "the icon sprite", 3, "image", ""),
    ("ogcard", "the link-preview card", 3, "image", ""),
    ("appicons", "the favicons and home-screen icons", 3, "image", ""),
    ("splash", "the splash screens", 3, "image", ""),
    ("regalia", "the REGALIA textures", 3, "texture", ""),
    ("aurum", "the AURUM textures", 3, "texture", ""),
    ("sw", "the service worker", 4, "runtime", ""),
    ("manifest", "the web app manifest", 4, "runtime", ""),
    ("headers", "the response headers", 4, "runtime", ""),
    ("storage", "on-device storage", 4, "runtime", "data"),
    ("feeds", "the market feed adapters", 4, "runtime", "data live"),
    ("pricefmt", "price formatting", 4, "runtime", "data"),
    ("deskgen", "the desk generator", 4, "tool", ""),
    ("domaingen", "the domain stamper", 4, "tool", ""),
    ("skingen", "the GENESIS skin generator", 4, "tool", ""),
    ("coingen", "the coin master", 4, "tool", ""),
    ("evergen", "the EVER NEXT builder", 4, "tool", ""),
    ("qa", "the QA suite", 4, "tool", ""),
    ("catalogs", "the catalogs", 4, "doc", ""),
    ("readme", "the README", 4, "doc", ""),
    ("glossarydata", "the glossary definitions", 4, "doc", ""),
    ("metadata", "the sitemap and page metadata", 4, "doc", ""),
]

VISIBLE = "page ui datapanel layout"
ASPECTS = [
    # id, name, rule, moves ("n:text"), bars
    ("type", "TYPE SCALE", dict(kinds=VISIBLE, exclude="progress"), [
        "a:List every font size used in {s} and map each one to the type scale.",
        "f:Raise any text in {s} that renders below the legibility floor.",
        "f:Give {s} one line-height per size step instead of per element.",
        "f:Replace letter-spacing workarounds in {s} with the size step that fits.",
        "f[data]:Keep the numerals in {s} tabular so digits never shift.",
        "a:View {s} at 200% browser zoom and record any clipped or overlapping text."],
        ["body text ≥ 14px, labels ≥ 11px at 390px", "desk text ≥ 7px as rendered on iPhone 13", "every size is a scale token"]),
    ("contrast", "CONTRAST", dict(kinds=VISIBLE), [
        "a:Measure every text and background pair in {s}.",
        "f:Raise any pair in {s} below the bar with a solid token colour, not opacity.",
        "a:Check {s} under each skin: GENESIS, REGALIA, AURUM and OFF.",
        "a:Check the focus rings and borders of {s} against their backgrounds.",
        "f:Replace opacity-dimmed text in {s} with a named muted colour token.",
        "a:View {s} in forced-colors (high contrast) mode and record what disappears."],
        ["4.5:1 body, 3:1 large text and UI edges", "7:1 body text (AAA)", "passes in forced-colors mode"]),
    ("spacing", "SPACING RHYTHM", dict(kinds=VISIBLE, exclude="progress"), [
        "a:Record every margin and padding in {s} against the 4px grid.",
        "f:Snap off-grid spacing in {s} to the nearest step.",
        "f:Make the vertical rhythm between siblings in {s} consistent.",
        "f:Give the frame of {s} equal optical padding on every side.",
        "f:Remove double spacing where borders and margins stack in {s}.",
        "f:Move the spacing of {s} onto shared tokens so one change updates every use."],
        ["4px grid", "named spacing tokens only", "rhythm identical at 390px and 1280px"]),
    ("align", "ALIGNMENT & GRID", dict(kinds=VISIBLE), [
        "a:Overlay the grid on {s} and note every element off the grid.",
        "f:Align the baselines of labels and values in {s}.",
        "f:Centre the icons in {s} optically, not just by bounding box.",
        "f:Make the edges of adjacent blocks in {s} share one line.",
        "a:Check {s} for half-pixel blur at DPR 2 and 3.",
        "f:Lock the column structure of {s} against changing content."],
        ["on the 12-column grid", "sub-pixel exact at DPR 3", "stable under live data changes"]),
    ("hierarchy", "HIERARCHY", dict(kinds="page datapanel layout", include="more termsheet deskcards glimmersheet panel storagecard"), [
        "h:Name the single most important thing in {s} and check that it reads first.",
        "f:Reduce competing emphasis in {s} to one hero per view.",
        "f:Order {s} so that reading order matches visual order.",
        "f:Give the headings in {s} a consistent level structure.",
        "f:Demote decorative labels in {s} below data labels.",
        "h:Show {s} to someone for five seconds and ask what they remember."],
        ["one clear primary per view", "heading levels never skip", "a new visitor reads it correctly at a glance"]),
    ("touch", "TOUCH TARGETS", dict(kinds="page ui", traits="interactive"), [
        "a:Measure every control in {s} and list any under the bar.",
        "f:Grow undersized targets in {s} with padding, not visual size.",
        "f:Separate adjacent targets in {s} so a thumb cannot hit two.",
        "f:Keep the controls of {s} clear of the home indicator and screen edges.",
        "f:Give the controls of {s} a pressed state that shows within one frame.",
        "h:Operate {s} one-handed on a 390px phone and record every stretch."],
        ["44×44px targets", "8px between targets", "reachable one-handed"]),
    ("focus", "FOCUS & KEYBOARD", dict(kinds="page ui", traits="interactive"), [
        "a:Tab through {s} and record the order and any trap.",
        "f:Give every control in {s} a visible focus ring.",
        "f:Make every function of {s} reachable by keyboard alone.",
        "f:Return focus to the trigger each time a view or sheet in {s} closes.",
        "f:Add arrow-key movement to every group of options in {s}.",
        "h:Operate {s} with switch access and record every dead end."],
        ["visible focus everywhere", "no traps, logical order", "arrow-key groups follow ARIA patterns"]),
    ("sr", "SCREEN-READER NAMING", dict(kinds="page ui datapanel"), [
        "a:Read {s} with VoiceOver and note every unnamed or misnamed element.",
        "f:Give each control in {s} an accessible name that matches its label.",
        "f:Hide the decoration in {s} from assistive technology.",
        "f[live|motion|interactive]:Announce changes in {s} politely, and no more often than needed.",
        "f[data]:Give the values in {s} their units in the accessible name.",
        "f:Add landmarks and headings so {s} can be navigated by rotor."],
        ["every control named", "live regions rate-limited", "full rotor navigation"]),
    ("motion", "MOTION DISCIPLINE", dict(kinds="page ui datapanel", traits="motion"), [
        "a:List every animation and transition in {s} with its duration.",
        "f:Remove any constant or looping motion from {s}.",
        "f:Give {s} an instant equivalent when reduced motion is on.",
        "f:Keep the motion in {s} under 250ms and tied to a user action.",
        "f:Animate {s} with transform and opacity only.",
        "a:Record any layout shift in {s} during motion."],
        ["no infinite animation", "reduced motion honoured", "zero layout shift"]),
    ("weight", "WEIGHT & SPEED", dict(kinds="page layout image texture"), [
        "a:Measure the first-load bytes of {s}.",
        "f:Cut the largest single cost in {s}.",
        "f:Serve {s} in a smaller format where one exists.",
        "f[image|texture]:Load {s} only when needed.",
        "a:Load {s} on a slow 3G profile and record the wait.",
        "f:Set a byte budget for {s} and record it with the build."],
        ["within the recorded budget", "budget cut by a quarter", "first render under 1s on 4G"]),
    ("offline", "OFFLINE", dict(kinds="page layout"), [
        "a:Open {s} offline after one visit and record what fails.",
        "f:Precache every file needed to render {s} offline.",
        "f:Make {s} say clearly what is unavailable offline.",
        "a:Open {s} offline right after a service-worker update.",
        "f:Keep {s} usable while the network flaps.",
        "a:Open {s} offline in a fresh browser profile after one visit."],
        ["renders offline after one visit", "states what is unavailable", "survives an update while offline"]),
    ("empty", "EMPTY STATE", dict(kinds="page ui datapanel", traits="data"), [
        "a:Show {s} with no data yet and record what appears.",
        "f:Replace blank or zero-filled output in {s} with an honest empty state.",
        "f:Tell readers what will fill {s} and when.",
        "f:Keep {s} the same size empty as full, so nothing jumps.",
        "f:Distinguish 'none yet' from 'zero' in {s}.",
        "a:Open {s} on a brand-new desk with no history."],
        ["no zeros stand in for missing data", "same size empty and full", "explains what fills it"]),
    ("error", "ERROR & FAILURE", dict(kinds="ui datapanel runtime page", traits="data live", exclude="metricrow provtag datapage"), [
        "a:Break each input of {s} in turn and record what happens.",
        "f:Make every failure of {s} visible, never silent.",
        "f:Keep {s} usable when one source fails.",
        "f:Log the failures of {s} where the operator can find them.",
        "f:Recover {s} automatically when the fault clears.",
        "t:Add a QA case that feeds malformed and out-of-range values to {s}."],
        ["never fails silently", "degrades per source", "recovers without a reload"]),
    ("stale", "STALENESS", dict(kinds="datapanel runtime", traits="live"), [
        "a:Stop the data behind {s} and record what appears.",
        "f:Show the age of the data in {s}.",
        "f:Mark {s} as stale once the data passes the stale threshold.",
        "f:Stop {s} extrapolating from stale data.",
        "f:Scale the stale threshold of {s} to the feed's update rate.",
        "a:Pause the feed for one, five and sixty minutes and record {s} each time."],
        ["age always visible", "stale is marked within one interval", "no extrapolation past stale"]),
    ("precision", "NUMERIC PRECISION", dict(kinds="datapanel", traits="live", include="pricefmt storagecard glimmersheet"), [
        "a:List every number in {s} with its decimals and units.",
        "f:Give the prices in {s} decimals that suit the asset's magnitude.",
        "f:Use significant figures, not fixed decimals, for tiny values in {s}.",
        "f:Never let {s} round a real value to zero.",
        "f[live|pricefmt]:Keep money, percentages and ratios in {s} in distinct formats.",
        "t:Add a QA case that checks {s} at US$0.0006, US$0.20, US$100 and US$84,000."],
        ["correct for every listed asset", "no non-zero value shows as zero", "one formatter for every number"]),
    ("prov", "PROVENANCE", dict(kinds="page ui datapanel runtime", traits="data", exclude="storage pricefmt"), [
        "a:Classify every value in {s}: observed, derived, inferred or model.",
        "f:Label the model and inferred values in {s} as such.",
        "f:Show the source of the observed values in {s}.",
        "f:Keep the inferred values in {s} visually distinct from observed ones.",
        "f:Remove any value from {s} that has no real source.",
        "f:Link {s} to the Data page's definitions."],
        ["every value classified", "sources named", "nothing without a source"]),
    ("copy", "COPY CLARITY", dict(kinds="page ui datapanel doc", exclude="progress metadata"), [
        "h[page|doc|ui]:Read {s} aloud and mark every sentence that stumbles.",
        "w:Cut the copy in {s} to the shortest version that keeps the meaning.",
        "w:Replace jargon in {s} with a glossary link or plain words.",
        "w[interactive]:Make each label in {s} say what the control does, not what it is.",
        "a:Check that every claim in {s} is literally true today.",
        "w:Keep the capitalisation and terms in {s} consistent with the glossary."],
        ["every claim literally true", "every term in the glossary", "readable by a new visitor"]),
    ("genesis", "GENESIS FIDELITY", dict(kinds="page ui datapanel layout texture", exclude="regalia aurum"), [
        "h:Compare {s} under GENESIS with the skin's principles.",
        "f:Remove any glow, noise or motion from {s} that GENESIS does not allow.",
        "f:Derive every ornament in {s} from QuadCOM geometry.",
        "f:Keep the ornament in {s} away from data ink.",
        "a:Check {s} under GENESIS at DPR 1, 2 and 3.",
        "a:Check the OFF rendering of {s} for anything missing or broken."],
        ["engraved, static, derived", "crisp at every DPR", "OFF is complete and clean"]),
    ("darkroom", "DARK-ROOM LEGIBILITY", dict(kinds=VISIBLE), [
        "h:View {s} at minimum screen brightness and note what disappears.",
        "f:Raise the faintest essential ink in {s}.",
        "f:Remove large bright areas from {s} that dazzle in the dark.",
        "h:View {s} with Night Shift and True Tone on.",
        "f[data]:Keep the status colours in {s} distinguishable when dim.",
        "h:View {s} on an OLED screen and check for black crush."],
        ["legible at minimum brightness", "no dazzle areas", "status still distinct when dim"]),
    ("small", "SMALL SCREENS", dict(kinds="page layout"), [
        "a:Render {s} at 320px wide and record every break.",
        "f:Stop anything in {s} forcing horizontal scroll.",
        "f:Reflow {s} instead of shrinking the layout.",
        "a:Render {s} at the largest accessibility text size.",
        "f:Keep the primary actions of {s} visible without scrolling.",
        "a:Render {s} in split-screen and slide-over widths."],
        ["no breaks at 320px", "reflows at largest text", "works in split view"]),
    ("large", "LANDSCAPE & LARGE", dict(kinds="page layout"), [
        "a:Render {s} in landscape and at 1920px and record wasted space.",
        "f:Cap the line length in {s} for comfortable reading.",
        "f:Use the extra width in {s} for context, not stretch.",
        "a:Render {s} on an iPad in both orientations.",
        "f:Keep {s} centred and balanced on ultrawide screens.",
        "a:Render {s} at 50% and 200% browser zoom."],
        ["no wasted or stretched space", "comfortable line length", "balanced on ultrawide"]),
    ("print", "PRINT & EXPORT", dict(kinds="page", exclude="notfound offline"), [
        "a:Print {s} and note what is lost or wasted.",
        "f:Remove navigation and ornament from {s} in print.",
        "f:Keep the text of {s} black on white in print.",
        "f:Show the link targets of {s} in print.",
        "f:Avoid page breaks inside the blocks of {s}.",
        "a:Export {s} to PDF and check that the PDF reads well."],
        ["clean print", "links shown", "no split blocks"]),
    ("cvd", "COLOUR-BLIND SAFETY", dict(kinds="datapanel", traits="live", include="provtag segment"), [
        "a:View {s} through protanopia, deuteranopia and tritanopia filters.",
        "f:Pair every colour meaning in {s} with a shape, sign or word.",
        "f[live]:Make up and down in {s} distinguishable without red and green.",
        "a[live]:Check the series in {s} stay separable in greyscale.",
        "f:Give every status colour in {s} a text equivalent.",
        "h:Ask a colour-blind reviewer to read {s}."],
        ["meaning never colour-only", "separable in greyscale", "reviewed by a colour-blind user"]),
    ("locale", "LOCALE READINESS", dict(kinds="datapanel", traits="live", include="pricefmt storagecard"), [
        "a:List every hard-coded format in {s}: currency, decimals, dates.",
        "f:Route every number in {s} through one locale-aware formatter.",
        "a:Check the layout of {s} with labels 40% longer.",
        "f:Use unambiguous dates and times in {s}.",
        "f:Mark the language of every text part in {s}.",
        "a:Render {s} with a comma decimal separator."],
        ["one formatter", "tolerates 40% longer labels", "language marked"]),
    ("determinism", "DETERMINISM", dict(kinds="tool texture doc", include="coins ogcard", exclude="readme glossarydata regalia aurum"), [
        "a[texture|doc|image]:Rebuild {s} twice and diff the outputs.",
        "f[tool]:Remove timestamps and randomness from what {s} writes.",
        "f[tool]:Pin every input of {s}.",
        "f[tool]:Make {s} fail loudly on unexpected input.",
        "w[texture|doc|image]:Record the exact command that produces {s}.",
        "a[tool]:Run {s} on another machine and diff the output."],
        ["byte-identical rebuilds", "fails on drift", "same on any machine"]),
    ("tests", "TEST COVERAGE", dict(kinds="page ui datapanel layout runtime tool"), [
        "a:List each job of {s} and the QA script that checks it.",
        "t:Add a QA check for the riskiest untested part of {s}.",
        "t:Make the failure messages of the QA checks for {s} name the cause.",
        "t:Run the QA checks for {s} at 390px and 1280px.",
        "t:Add a regression check for the last bug found in {s}.",
        "t:Time the QA checks for {s} and keep them fast."],
        ["riskiest part checked", "every past bug has a check", "suite under five minutes"]),
    ("docs", "DOCUMENTATION", dict(kinds="tool runtime texture image"), [
        "a:Check the README explains {s} in one paragraph.",
        "w:Document the reason for {s}, not just the mechanics.",
        "w:Give {s} a worked example in the README.",
        "w:List the invariants of {s}.",
        "w:Record the known limits of {s} honestly.",
        "a:Check the documentation of {s} still matches the code."],
        ["one clear paragraph", "invariants listed", "docs match code"]),
    ("security", "SECURITY & PRIVACY", dict(kinds="runtime page", exclude="pricefmt"), [
        "a:List everything stored, sent and received by {s}.",
        "f:Remove any data from {s} that is not needed.",
        "a:Check {s} under the site's response headers.",
        "f:Remove every unneeded third-party request from {s}.",
        "f[data|runtime]:Validate every external value that reaches {s}.",
        "a:Review {s} against a strict content-security policy."],
        ["minimal data", "valid under strict headers", "passes a CSP"]),
    ("caching", "CACHING & DELIVERY", dict(kinds="page image texture", include="sw manifest"), [
        "a:Record the browser and service-worker caching of {s}.",
        "f:Version {s} so each new build replaces the old copy.",
        "f:Make the revalidation of {s} non-blocking.",
        "a:Deploy twice in a row and confirm the new version of {s} arrives each time.",
        "f:Precompress {s} where the host allows.",
        "f:Cache {s} for as long as the content is immutable."],
        ["new builds always reach users", "never blocks render", "immutable assets cached long"]),
    ("consistency", "CONSISTENCY", dict(kinds=VISIBLE), [
        "a:Compare {s} with the nearest sibling and list the differences.",
        "f:Replace one-off values in {s} with shared tokens.",
        "f:Make {s} behave like the other parts of the same kind.",
        "f:Match the corner radii, borders and weights in {s} to the system.",
        "f:Remove duplicate CSS rules that style {s}.",
        "f:Cut the !important rules that affect {s}."],
        ["no one-off values", "no duplicate rules", "no !important wars"]),
    ("resilience", "RESILIENCE", dict(kinds="runtime layout", exclude="headers manifest pricefmt"), [
        "a:Interrupt {s} mid-operation and record the state left behind.",
        "f:Make {s} restart cleanly after a crash.",
        "f:Bound every queue and buffer in {s}.",
        "a:Run {s} on an old phone and record the memory use.",
        "f[data|runtime]:Survive a storage-quota error in {s}.",
        "a:Run {s} for 24 hours and check for drift or leaks."],
        ["clean restart", "bounded resources", "24-hour soak clean"]),
    ("craft", "CRAFT DETAIL", dict(kinds="image texture ui"), [
        "h:Inspect {s} at 400% zoom and list every imperfection.",
        "f:Fix the smallest visible flaw in {s}.",
        "a:Check the antialiasing of {s} on light and dark backgrounds.",
        "f:Align {s} to whole pixels at every DPR.",
        "f:Balance the optical weight of {s} with the neighbouring elements.",
        "h:Compare {s} with the best reference you know and close one gap."],
        ["no visible flaw at 100%", "no flaw at 400%", "stands beside the best reference"]),
]

# Depth text per move nature, so every stage fits the move it follows.
DEPTHS = ["OBSERVE", "REFINE", "SYSTEMATISE", "PROVE", "SUSTAIN"]
DEPTH_TEXT = {
    "a": ["Run it once and record every finding; change nothing yet.", "Fix each recorded finding.",
          "Turn the fixes into shared rules, tokens or templates.", "Automate the audit as a QA check that fails on a regression.",
          "Run the automated audit in every build so none ships without it."],
    "f": ["First list every place this applies; change nothing yet.", "Make the change in each place.",
          "Move the change into a shared token, rule or component.", "Add a QA check that fails if it regresses.",
          "Run its regression check in every build so none ships without it."],
    "w": ["First list every place this applies; change nothing yet.", "Rewrite each one.",
          "Add the rule to a shared style guide that every page and tool follows.", "Add a QA check that fails when the rule is broken.",
          "Run that check in every build so none ships without it."],
    "t": ["First list the cases worth covering.", "Write the check for the most important case.",
          "Share its helpers so other checks can reuse them.", "Plant the regression once to confirm the check fails.",
          "Run it in every build so none ships without it."],
    "h": ["Do it once and write down what you saw.", "Fix what it revealed.",
          "Write the procedure down so anyone can repeat it.", "Have a second person repeat it and compare notes.",
          "Put it on the release checklist."],
}


def move_parts(move):
    """'f[data|live]:text' -> ('f', {'data', 'live'}, 'text'); no brackets means no condition."""
    head, text = move.split(":", 1)
    cond = set(head[2:-1].split("|")) if "[" in head else set()
    return head[0], cond, text

def move_applies(surface, move):
    cond = move_parts(move)[1]
    return not cond or bool(cond & ({surface[0], surface[3]} | set(surface[4].split())))

def move_mask(surface, aspect):
    return sum(1 << i for i, m in enumerate(aspect[3]) if move_applies(surface, m))

def applies(surface, aspect):
    _, _, _, kind, traits = surface
    rule = aspect[2]
    if surface[0] in rule.get("exclude", "").split():
        return False
    if surface[0] in rule.get("include", "").split():
        return True
    if kind not in rule["kinds"].split():
        return False
    need = rule.get("traits", "").split()
    return not need or bool(set(need) & set(traits.split()))
