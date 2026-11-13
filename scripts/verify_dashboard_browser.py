"""Run Day 15 Chromium QA against a fresh, data-free Streamlit tree."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
from urllib.parse import urlsplit
from urllib.request import ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
INPUTS = (
    ".streamlit/config.toml", "dashboard/app.py", "dashboard/synthetic_contract.py",
    "dashboard/synthetic_fixture.json", "scripts/verify_synthetic_dashboard.py",
    "scripts/verify_dashboard_browser.py",
)
VIEWPORTS = ((375, 812), (390, 844), (768, 1024), (1366, 768), (1440, 900))
TABS = ("Overview", "Synthetic Experiment", "Synthetic Policy Evaluation", "Methodology & Limitations")
SLUGS = ("overview", "experiment", "policy", "methodology")
LABELS = {"conversion": "Conversion", "visit": "Visit", "spend": "Spend"}
FIXTURE_FILE_SHA = "9ae99ded05c4b2123a9abb5984a34de78813f8212ac886270daed77dad040b58"
CONTENT_SHA = "4508bd68cd83907a835642075e14fb20c5c11c5ded794358e18397c6a5e38ba0"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, data):
    with path.open("x", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def utc():
    return datetime.now(timezone.utc).isoformat()


def serve(protected_root, port):
    sys.path.insert(0, str(ROOT))
    from scripts.verify_synthetic_dashboard import access_hook, GROUPS

    attempts = Counter(dict.fromkeys(GROUPS, 0))
    check = access_hook(protected_root, ROOT, attempts)

    def audit(event, args):
        if event == "socket.getaddrinfo" and args[0] == "127.0.0.1":
            return  # Uvicorn resolves the explicitly bound loopback address.
        try:
            check(event, args)
        except PermissionError:
            print("DAY15_BLOCKED " + json.dumps(dict(attempts)), flush=True)
            raise

    sys.addaudithook(audit)
    from streamlit.web.cli import main
    main(["run", "dashboard/app.py", "--server.address", "127.0.0.1",
          "--server.port", str(port), "--server.headless", "true",
          "--server.fileWatcherType", "none", "--browser.gatherUsageStats", "false"])


def wait_for_server(child, url):
    opener = build_opener(ProxyHandler({}))
    until = time.monotonic() + 20
    while time.monotonic() < until:
        if child.poll() is not None:
            raise RuntimeError(f"Streamlit exited {child.returncode}")
        try:
            with opener.open(f"{url}/_stcore/health", timeout=0.5) as reply:
                if reply.status == 200 and reply.read().strip() == b"ok":
                    return
        except OSError:
            time.sleep(.2)
    raise RuntimeError("Loopback Streamlit health timeout")


def table_text(panel):
    return [table.evaluate(r"""t => Array.from(t.rows, row =>
        Array.from(row.cells, cell => cell.innerText.trim().replace(/\s+/g, ' ')))""")
        for table in panel.locator("table").all()]


def expected_rows(fixture, tab, outcome):
    if tab == 1:
        return [[[r["arm"], str(r["n"]), *(f"{r[key]:.3f}" for key in LABELS)]
                 for r in fixture["arm_results"]]]
    absolute, delta = [], []
    for row in fixture["policy_results"]:
        if row["outcome"] != outcome:
            continue
        policy = row["policy"]
        estimate = f"{row['estimate']:.3f}"
        interval = f"[{row['low']:.3f}, {row['high']:.3f}]"
        if row["kind"] == "absolute":
            label = fixture["metadata"]["policy_definitions"][policy]["label"]
            absolute.append([f"{policy} · {label}", estimate, interval])
        else:
            delta.append([policy, estimate, interval, f"{row['p_value']:.3g}", f"{row['p_holm']:.3g}"])
    return [absolute, delta]


def geometry(panel):
    return panel.evaluate(r"""panel => {
        const r = e => {const b = e.getBoundingClientRect();
            return {x:b.x, y:b.y, width:b.width, height:b.height, right:b.right};};
        const main = document.querySelector('[data-testid="stMain"]');
        return {
            viewport: [innerWidth, innerHeight],
            document_width: document.documentElement.scrollWidth,
            main_width: main.clientWidth, main_scroll_width: main.scrollWidth,
            main_height: main.clientHeight, main_scroll_height: main.scrollHeight,
            tabs: [...document.querySelectorAll('[role="tab"]')].map(e => ({
                label:e.innerText, ...r(e), scroll_width:e.scrollWidth, client_width:e.clientWidth})),
            metrics: [...panel.querySelectorAll('[data-testid="stMetricValue"]')].map(e => ({
                label:e.innerText, ...r(e), scroll_width:e.scrollWidth, client_width:e.clientWidth})),
            radio_targets: [...panel.querySelectorAll('[role="radiogroup"] label')].map(e => ({
                label:e.innerText,...r(e)})),
            tables: [...panel.querySelectorAll('table')].map(e => {
                const parent = e.closest('[data-testid="stTable"]');
                const scroll = [e, ...parents(e, panel)].find(x =>
                    x.scrollWidth > x.clientWidth + 1 && /auto|scroll/.test(getComputedStyle(x).overflowX));
                const old = scroll?.scrollLeft ?? 0;
                if (scroll) scroll.scrollLeft = scroll.scrollWidth;
                const reached = scroll?.scrollLeft ?? 0;
                const last = e.rows[0].cells[e.rows[0].cells.length-1];
                const visible = !scroll || r(last).right <= r(scroll).right + 1;
                if (scroll) scroll.scrollLeft = old;
                const wrapped = [...e.querySelectorAll('tbody td')].filter(cell => {
                    if (!/^\[|e[+-][0-9]+$/i.test(cell.textContent.trim())) return false;
                    const walker = document.createTreeWalker(cell, NodeFilter.SHOW_TEXT);
                    const lines = new Set();
                    while (walker.nextNode()) {
                        if (!walker.currentNode.textContent.trim()) continue;
                        const range = document.createRange();
                        range.selectNode(walker.currentNode);
                        for (const box of range.getClientRects()) lines.add(Math.round(box.top));
                    }
                    return lines.size > 1;
                }).map(cell => cell.textContent.trim());
                return {...r(e), wrapper:parent ? r(parent) : null, horizontal_scroll:!!scroll,
                    max_scroll:scroll ? scroll.scrollWidth-scroll.clientWidth : 0,
                    reached_scroll:reached, last_column_reachable:visible, wrapped_numeric_cells:wrapped};
            }),
            charts: [...panel.querySelectorAll('.vega-embed canvas, .vega-embed svg.marks')].map(e =>
                ({...r(e), renderer:e.tagName.toLowerCase()})),
        };
        function* parents(node, stop) {
            while (node.parentElement && node !== stop) {node=node.parentElement; yield node;}
        }
    }""")


def chart_evidence(chart, fixture, tab, outcome, axis):
    from playwright.sync_api import expect

    svg = chart.locator("svg.marks")
    expect(svg.get_by_text(axis, exact=True)).to_be_visible()
    units = fixture["metadata"]["unit_definitions"][outcome]
    if tab == 1:
        labels = [f"{r['arm']} · {LABELS[outcome]} {r[outcome]:.3f} {units['absolute']}"
                  for r in fixture["arm_results"]]
    else:
        labels = [
            f"{r['policy']} · {r['estimate']:.3f} {units['incremental']} · 95% CI [{r['low']:.3f}, {r['high']:.3f}]"
            for r in fixture["policy_results"] if r["outcome"] == outcome and r["kind"] == "incremental"
        ]
    for label in labels:
        expect(svg.locator(f"[aria-label={json.dumps(label, ensure_ascii=False)}]")).to_be_visible()
    intervals = svg.evaluate("""root => {
        const bounds = root.getBoundingClientRect();
        return [...root.querySelectorAll('g.mark-rule.role-mark line')].map(e => {
            const r = e.getBoundingClientRect();
            return {width:r.width, height:r.height,
                contained:r.left>=bounds.left && r.right<=bounds.right &&
                          r.top>=bounds.top && r.bottom<=bounds.bottom};
        }).filter(x => x.width > 0 && x.height < 1);
    }""")
    if tab == 2:
        assert len(intervals) == 3 and all(r["contained"] for r in intervals), intervals
    return {"axis": axis, "mark_labels": labels, "visible_ci_rules": intervals}


def capture(page, path, screenshots, width, height):
    page.screenshot(path=path, animations="disabled", full_page=True)
    screenshots.append({"file": path.name, "sha256": digest(path), "viewport": [width, height], "utc": utc()})


def scroll_top(page):
    page.locator('[data-testid="stMain"]').evaluate("e => e.scrollTop = 0")


def inspect_view(browser, url, width, height, fixture, shots, *, resize_check=False):
    from playwright.sync_api import expect

    port = urlsplit(url).port

    def local(address):
        target = urlsplit(address)
        return target.hostname == "127.0.0.1" and target.port == port

    context = browser.new_context(viewport={"width": width, "height": height},
                                  has_touch=width < 800, is_mobile=width < 800,
                                  device_scale_factor=1, service_workers="block")
    page = context.new_page()
    errors, warnings, requests, socket_urls, blocked, responses, screenshots, steps, layout_issues = (
        [] for _ in range(9)
    )
    page.set_default_timeout(7000)
    page.on("pageerror", lambda error: errors.append(str(error)))

    def console(message):
        if message.type == "error":
            errors.append(message.text)
        if message.type == "warning":
            warnings.append(message.text)

    def handle(route):
        if local(route.request.url):
            route.continue_()
        else:
            blocked.append(route.request.url)
            route.abort("blockedbyclient")

    def websocket(route):
        if local(route.url):
            route.connect_to_server()
        else:
            blocked.append(route.url)
            route.close()

    page.on("console", console)
    page.on("request", lambda request: requests.append(request.url))
    page.on("response", lambda response: responses.append(response.status) if response.status >= 400 else None)
    page.on("websocket", lambda connection: socket_urls.append(connection.url))
    context.route("**/*", handle)
    context.route_web_socket("**/*", websocket)
    prefix = f"{width}x{height}"
    case_error = None
    try:
        page.goto(url, wait_until="domcontentloaded")
        expect(page.get_by_role("heading", name="이메일 실험과 정책 평가")).to_be_visible()
        for i, title in enumerate(TABS):
            page.get_by_role("tab", name=title, exact=True).click()
            panel = page.get_by_role("tabpanel", name=title, exact=True)
            expect(panel).to_be_visible()
            expect(panel.get_by_text("SYNTHETIC", exact=False).first).to_be_visible()
            if i == 0:
                expect(panel.get_by_text("12,909", exact=True)).to_be_visible()
                expect(panel.get_by_text(fixture["metadata"]["fixture_id"], exact=False)).to_be_visible()
                for item in ("No E-Mail", "Mens E-Mail", "Womens E-Mail", "NOT_EVALUATED"):
                    expect(panel.get_by_text(item, exact=False).first).to_be_visible()
            if i == 3:
                for item in ("3군 무작위 실험", "ITT", "HT IPS", "1/3", "공분산", "Holm",
                             "pointwise 95% CI", "비용과 마진", "NOT_EVALUATED", "INCONCLUSIVE"):
                    expect(panel.get_by_text(item, exact=False).first).to_be_visible()
            choices = LABELS if i in (1, 2) else (None,)
            for outcome in choices:
                chart = panel.locator(".vega-embed").first
                chart_record = None
                if outcome:
                    radio = panel.get_by_role("radiogroup").locator("label").filter(has_text=LABELS[outcome])
                    radio.tap() if width < 800 else radio.click()
                    units = fixture["metadata"]["unit_definitions"][outcome]
                    expected_axis = (f"{LABELS[outcome]} ({units['absolute']})" if i == 1
                                     else f"P0 대비 차이 ({units['incremental']})")
                    chart.locator("canvas, svg.marks").first.wait_for(state="visible")
                    if i == 2:
                        expect(panel.get_by_text(expected_axis, exact=True).first).to_be_visible()
                    for table_index, rows in enumerate(expected_rows(fixture, i, outcome)):
                        for row in rows:
                            rendered = panel.locator("table").nth(table_index).get_by_role("row").filter(
                                has=page.get_by_text(row[0], exact=True)
                            )
                            expect(rendered.get_by_text(row[1], exact=True)).to_be_attached()
                    actual = table_text(panel)
                    for displayed, expected in zip(actual, expected_rows(fixture, i, outcome), strict=True):
                        assert displayed[-len(expected):] == expected, (displayed, expected)
                    chart_record = chart_evidence(chart, fixture, i, outcome, expected_axis)
                scroll_top(page)
                layout = geometry(panel)
                if max(layout["document_width"], layout["main_scroll_width"]) > width + 1:
                    layout_issues.append(f"{title}/{outcome}: page overflow")
                if any(tab["x"] < 0 or tab["right"] > width + 1
                       or tab["scroll_width"] > tab["client_width"] + 1 for tab in layout["tabs"]):
                    layout_issues.append(f"{title}/{outcome}: clipped tab")
                if width <= 640 and any(tab["height"] < 44 for tab in layout["tabs"]):
                    layout_issues.append(f"{title}/{outcome}: small mobile tab")
                if width < 800 and any(r["height"] < 44 or r["width"] < 44 for r in layout["radio_targets"]):
                    layout_issues.append(f"{title}/{outcome}: small touch target")
                if i == 0 and (len(layout["metrics"]) != 3
                              or len({round(k["y"]) for k in layout["metrics"]}) != 1
                              or any(k["right"] > width + 1 or k["scroll_width"] > k["client_width"] + 1
                                     for k in layout["metrics"])):
                    layout_issues.append(f"{title}: KPI layout or text clipped")
                if any(not t["last_column_reachable"] or
                       t["horizontal_scroll"] and t["reached_scroll"] < t["max_scroll"] - 1
                       for t in layout["tables"]):
                    layout_issues.append(f"{title}/{outcome}: incomplete table scroll")
                if any(t["wrapped_numeric_cells"] for t in layout["tables"]):
                    layout_issues.append(f"{title}/{outcome}: wrapped CI or scientific notation")
                assert "ROI" not in panel.inner_text()
                assert not page.locator('[data-testid="stException"]').count()
                steps.append({"tab": title, "outcome": outcome, "fixture_id": fixture["metadata"]["fixture_id"],
                              "units": units if outcome else None, "layout": layout,
                              "tables": table_text(panel), "chart": chart_record, "status": "PASS"})
                if outcome in (None, "conversion"):
                    capture(page, shots / f"{prefix}_{SLUGS[i]}.png", screenshots, width, height)
                if outcome:
                    chart.scroll_into_view_if_needed()
                    chart.screenshot(path=shots / f"{prefix}_{SLUGS[i]}_{outcome}_chart.png", animations="disabled")
                    name = shots / f"{prefix}_{SLUGS[i]}_{outcome}_chart.png"
                    screenshots.append({"file": name.name, "sha256": digest(name), "viewport": [width, height],
                                        "utc": utc()})
                if i == 2 and outcome == "spend":
                    panel.locator("table").last.scroll_into_view_if_needed()
                    capture(page, shots / f"{prefix}_policy_spend_table.png", screenshots, width, height)
                    if width <= 640:
                        panel.locator("table").last.evaluate("""t => {
                            for (let e=t.parentElement; e; e=e.parentElement)
                                if (e.scrollWidth > e.clientWidth + 1 &&
                                    /auto|scroll/.test(getComputedStyle(e).overflowX)) {
                                    e.scrollLeft=e.scrollWidth; break;
                                }
                        }""")
                        capture(page, shots / f"{prefix}_policy_spend_table_right.png", screenshots, width, height)
                if layout["main_scroll_height"] > layout["main_height"] + 1:
                    actual_scroll = page.locator('[data-testid="stMain"]').evaluate(
                        "e => {e.scrollTop=e.scrollHeight; return e.scrollTop;}"
                    )
                    assert actual_scroll > 0
                    steps[-1]["vertical_scroll_px"] = actual_scroll
                    if i == 3 and width <= 640:
                        capture(page, shots / f"{prefix}_methodology_bottom.png", screenshots, width, height)
        page.get_by_role("tab", name="Overview", exact=True).click()
        expect(page.get_by_text(fixture["metadata"]["fixture_id"], exact=False)).to_be_visible()
        page.reload(wait_until="domcontentloaded")
        expect(page.get_by_text(fixture["metadata"]["fixture_id"], exact=False)).to_be_visible()
        steps.append({"tab": "Overview", "action": "return_and_reload", "status": "PASS"})
        if resize_check and width <= 390:
            page.set_viewport_size({"width": height, "height": width})
            panel = page.get_by_role("tabpanel", name="Overview", exact=True)
            expect(panel.get_by_text("12,909", exact=True)).to_be_visible()
            layout = geometry(panel)
            assert layout["viewport"] == [height, width]
            assert max(layout["document_width"], layout["main_scroll_width"]) <= height + 1
            steps.append({"tab": "Overview", "action": "landscape_viewport_resize", "layout": layout, "status": "PASS"})
            capture(page, shots / f"{prefix}_landscape_resize.png", screenshots, height, width)
        assert socket_urls and all(local(address) for address in socket_urls)
        assert not (errors or responses or blocked or layout_issues), (errors, responses, blocked, layout_issues)
    except Exception as error:
        case_error = f"{type(error).__name__}: {error}"
        capture(page, shots / f"{prefix}_failure.png", screenshots, width, height)
    finally:
        context.close()
    return {
        "viewport": [width, height], "touch_emulated": width < 800, "steps": steps,
        "status": "FAIL" if case_error else "PASS", "error": case_error, "screenshots": screenshots,
        "console_errors": errors, "console_warnings": warnings, "http_error_statuses": responses,
        "layout_issues": layout_issues,
        "local_websockets": len(socket_urls), "external_attempts_blocked": blocked,
        "local_http_requests": sum(local(address) for address in requests),
    }


def main(args):
    from playwright.sync_api import sync_playwright

    output = args.output.resolve()
    output.mkdir(parents=True)
    shots = output / "browser_screenshots"
    shots.mkdir()
    tree = output / "isolated"
    copied = {}
    for name in INPUTS:
        path = tree / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, path)
        copied[name] = digest(path)
    assert copied["dashboard/synthetic_fixture.json"] == FIXTURE_FILE_SHA
    doc = json.loads((tree / "dashboard/synthetic_fixture.json").read_bytes())
    fixture = doc["payload"]
    payload_sha = hashlib.sha256(json.dumps(fixture, sort_keys=True, separators=(",", ":")).encode("ascii")).hexdigest()
    assert doc["content_sha256"] == payload_sha == CONTENT_SHA
    assert set(copied) == {f.relative_to(tree).as_posix() for f in tree.rglob("*") if f.is_file()}
    started_at = utc()
    command = [str(args.server_python.resolve()), "-I", "-B", "scripts/verify_dashboard_browser.py",
               "--serve", "--protected-root", str(ROOT), "--port", str(args.port)]
    url = f"http://127.0.0.1:{args.port}"
    with (output / "server.log").open("xb") as log:
        child = subprocess.Popen(command, cwd=tree, stdout=log, stderr=subprocess.STDOUT,
                                 creationflags=0x08000000 if os.name == "nt" else 0)
        try:
            wait_for_server(child, url)
            with sync_playwright() as pw:
                if args.engine == "webkit":
                    browser = pw.webkit.launch(headless=True)
                else:
                    browser = pw.chromium.launch(channel=args.channel, headless=True,
                                                 args=["--disable-background-networking", "--no-proxy-server"])
                try:
                    browser_version = browser.version
                    records = [inspect_view(browser, url, *viewport, fixture, shots,
                                            resize_check=args.engine == "webkit") for viewport in VIEWPORTS]
                finally:
                    browser.close()
        finally:
            if child.poll() is None:
                child.terminate()
            child.wait(timeout=10)
    log = (output / "server.log").read_text(encoding="utf-8", errors="replace")
    blocked = [json.loads(line.split("DAY15_BLOCKED ", 1)[1]) for line in log.splitlines()
               if "DAY15_BLOCKED " in line]
    save(output / "browser_environment.json", {
        "os": platform.platform(), "python": platform.python_version(), "playwright": version("playwright"),
        "engine": args.engine, "channel": args.channel if args.engine == "chromium" else None,
        "browser_version": browser_version, "started_at_utc": started_at,
        "server": url, "server_command": command, "copied_input_hashes": copied,
        "fixture_id": fixture["metadata"]["fixture_id"], "fixture_sha256": FIXTURE_FILE_SHA,
        "content_sha256": CONTENT_SHA, "browser_mode": "headless viewport/touch emulation",
    })
    counts = dict(Counter(record["status"] for record in records))
    save(output / "browser_matrix.json", {"counts": counts, "results": records, "server_blocked_events": blocked})
    print(json.dumps({"counts": counts, "failures": [r["error"] for r in records if r["error"]],
                      "server_blocked_events": blocked}, ensure_ascii=False))
    return int(counts.get("FAIL", 0) > 0 or bool(blocked))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--server-python", type=Path)
    parser.add_argument("--channel", choices=("chrome", "msedge"), default="chrome")
    parser.add_argument("--engine", choices=("chromium", "webkit"), default="chromium")
    parser.add_argument("--port", type=int, default=8501)
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--protected-root", type=Path)
    args = parser.parse_args()
    if args.serve:
        serve(args.protected_root, args.port)
    else:
        if not args.output or not args.server_python:
            parser.error("--output and --server-python are required")
        sys.exit(main(args))
