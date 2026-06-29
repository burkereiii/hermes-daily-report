#!/usr/bin/env python3
"""Hermes Daily Report Generator v4.2
Fills template.html placeholders with live data, writes index.html + archive.
"""
import subprocess, json, datetime, os, re, sys, tempfile

REPORTS_DIR = r"C:\Users\沙河马\hermes-reports"
TEMPLATE = os.path.join(REPORTS_DIR, "template.html")


def run(cmd, timeout=30):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except Exception as e:
        return "", str(e), 1


def run_ps(script, timeout=30):
    """Run a PowerShell script snippet, avoiding bash $ expansion issues."""
    # Write to temp file to avoid shell escaping hell
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.ps1', delete=False, encoding='utf-8')
    tmp.write(script)
    tmp.close()
    try:
        r = subprocess.run(['powershell', '-File', tmp.name], capture_output=True, text=True, timeout=timeout)
        os.unlink(tmp.name)
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except Exception as e:
        try: os.unlink(tmp.name)
        except: pass
        return "", str(e), 1


def human_bytes(n):
    if n < 1024: return f"{n}B"
    if n < 1024*1024: return f"{n/1024:.1f}K"
    if n < 1024*1024*1024: return f"{n/(1024*1024):.1f}M"
    return f"{n/(1024*1024*1024):.2f}G"


def human_num(n):
    if n is None: return "—"
    n = int(n)
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if n >= 1_000: return f"{n/1_000:.1f}K"
    return str(n)


def collect_insights():
    """Collect core metrics from hermes insights (text output, not JSON)."""
    out, err, rc = run("hermes insights --days 1", timeout=60)
    data = {
        "TOKEN_TOTAL": "—", "SESSION_COUNT": "0", "MESSAGE_COUNT": "0",
        "TOOL_COUNT": "0", "MODEL_NAME": "—", "MODEL_PROVIDER": "—",
        "DESKTOP_MSGS": "0", "FEISHU_MSGS": "0", "WECHAT_MSGS": "0",
    }
    # Parse formatted text output (many fields share lines — use re.search)
    for line in out.split("\n"):
        line = line.strip()
        # Overview fields (may share lines: "Sessions: 9   Messages: 2,041")
        m = re.search(r'Sessions:\s+([\d,]+)', line)
        if m: data["SESSION_COUNT"] = m.group(1).replace(",", "")
        m = re.search(r'Messages:\s+([\d,]+)', line)
        if m: data["MESSAGE_COUNT"] = m.group(1).replace(",", "")
        m = re.search(r'Tool calls:\s+([\d,]+)', line)
        if m: data["TOOL_COUNT"] = m.group(1).replace(",", "")
        m = re.search(r'Total tokens:\s+([\d,]+)', line)
        if m: data["TOKEN_TOTAL"] = human_num(int(m.group(1).replace(",", "")))
        # Platform rows (columns: Platform, Sessions, Messages, Tokens)
        if re.match(r'^(tui|desktop|cli)\s+\d+', line):
            parts = line.split()
            data["DESKTOP_MSGS"] = parts[2].replace(",", "") if len(parts) >= 3 else "0"
        elif re.match(r'^weixin\s+\d+', line) or re.match(r'^wechat\s+\d+', line):
            parts = line.split()
            data["WECHAT_MSGS"] = parts[2].replace(",", "") if len(parts) >= 3 else "0"
        elif re.match(r'^feishu\s+\d+', line):
            parts = line.split()
            data["FEISHU_MSGS"] = parts[2].replace(",", "") if len(parts) >= 3 else "0"
        # Model info
        m = re.match(r'(deepseek-v\d[\w-]*|gpt-[\d.]+|claude[\w.-]*)\s+\d+\s+[\d,]+', line)
        if m:
            data["MODEL_NAME"] = m.group(1)
            # Determine provider from model name
            if "deepseek" in m.group(1).lower():
                data["MODEL_PROVIDER"] = "DeepSeek"
            elif "gpt" in m.group(1).lower():
                data["MODEL_PROVIDER"] = "OpenAI"
            elif "claude" in m.group(1).lower():
                data["MODEL_PROVIDER"] = "Anthropic"
            else:
                data["MODEL_PROVIDER"] = "—"
    return data


def collect_host():
    """Collect Windows host metrics via PowerShell temp file to avoid bash $ expansion."""
    data = {"CPU_USAGE": "—", "MEM_GB": "—", "MEM_USAGE": "—", "DISK_GB": "—", "DISK_USAGE": "—"}

    # CPU
    out, _, _ = run_ps("(Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average")
    if out and out.replace('.', '').replace('-', '').isdigit():
        data["CPU_USAGE"] = str(int(float(out)))

    # Memory
    out, _, _ = run_ps("""
$os = Get-CimInstance Win32_OperatingSystem
$t = [math]::Round($os.TotalVisibleMemorySize / 1MB)
$f = [math]::Round($os.FreePhysicalMemory / 1MB)
Write-Output "$t|$f"
""")
    if "|" in out:
        parts = out.strip().split("|")
        try:
            total_mb = float(parts[0])
            free_mb = float(parts[1])
            data["MEM_GB"] = str(int(total_mb))  # total_mb is already ~GB (TotalVisibleMemorySize(KB) / 1MB)
            data["MEM_USAGE"] = str(round((1 - free_mb / total_mb) * 100))
        except: pass

    # Disk C:
    out, _, _ = run_ps("""
$d = Get-PSDrive C
$used = [math]::Round($d.Used / 1GB, 1)
$total = [math]::Round(($d.Used + $d.Free) / 1GB, 1)
Write-Output "$used|$total"
""")
    if "|" in out:
        parts = out.strip().split("|")
        try:
            used = float(parts[0])
            total = float(parts[1])
            data["DISK_GB"] = str(used)
            data["DISK_USAGE"] = str(round(used/total*100))
        except: pass

    return data


def collect_storage():
    """Collect storage metrics."""
    data = {"CACHE_SIZE": "—", "DB_SIZE": "—", "MEMORY_COUNT": "—"}

    # Cache size (use Windows path for cmd.exe subprocess)
    out, _, _ = run('bash -c "du -sh /d/Hermes/cache/ 2>/dev/null | cut -f1"')
    if out:
        data["CACHE_SIZE"] = out.strip()

    # DB size
    out, _, _ = run('bash -c "wc -c < /d/Hermes/state.db 2>/dev/null || echo 0"')
    try:
        data["DB_SIZE"] = human_bytes(int(out.strip()))
    except: pass

    # Memory entries count (hermes memory has no 'list' subcommand)
    data["MEMORY_COUNT"] = "—"

    return data


def collect_cost():
    return {"YESTERDAY_COST": "—", "COST_NOTE": "余额快照待恢复"}


def fill_template(data: dict, date_str: str, weekday: str):
    """Substitute all placeholders in template."""
    data["REPORT_DATE"] = date_str
    data["REPORT_WEEKDAY"] = weekday

    with open(TEMPLATE, "r", encoding="utf-8") as f:
        html = f.read()

    for key, val in data.items():
        html = html.replace("{{" + key + "}}", str(val))

    # Catch any remaining unfilled placeholders
    remaining = re.findall(r'\{\{\s*(\w+)\s*\}\}', html)
    if remaining:
        print(f"⚠️ 警告: {len(remaining)} 个占位符未填充: {remaining}")

    return html


def main():
    today = datetime.date.today()
    date_str = today.strftime("%Y-%m-%d")
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    weekday = weekdays[today.weekday()]

    print(f"📊 采集 {date_str} ({weekday}) 数据...")

    data = {}
    print("  1/6 insights...")
    data.update(collect_insights())
    print(f"     Token: {data['TOKEN_TOTAL']} | 会话: {data['SESSION_COUNT']} | 消息: {data['MESSAGE_COUNT']}")

    print("  2/6 gateway...")
    gw_out, _, _ = run("hermes gateway status", timeout=15)
    m = re.search(r'PID:\s*(\d+)', gw_out)
    data["GATEWAY_PID"] = m.group(1) if m else "N/A"
    data["GATEWAY_STATUS"] = "运行中" if ("running" in gw_out.lower() or "运行" in gw_out) else "已停止"
    data["GATEWAY_STATUS_CLASS"] = "online" if data["GATEWAY_STATUS"] == "运行中" else "offline"
    data["GATEWAY_DOT_CLASS"] = "dot-online" if data["GATEWAY_STATUS"] == "运行中" else "dot-offline"
    data["WECHAT_STATUS"] = "未连接"; data["WECHAT_STATUS_CLASS"] = "offline"; data["WECHAT_DOT_CLASS"] = "dot-offline"
    data["FEISHU_STATUS"] = "未连接"; data["FEISHU_STATUS_CLASS"] = "offline"; data["FEISHU_DOT_CLASS"] = "dot-offline"
    print(f"     PID: {data['GATEWAY_PID']} | 状态: {data['GATEWAY_STATUS']}")

    print("  3/6 cron...")
    cron_out, _, _ = run("hermes cron list", timeout=10)
    cron_lines = [l.strip() for l in cron_out.split("\n") if l.strip() and not l.lower().startswith("no ")]
    data["CRON_TOTAL"] = str(len(cron_lines))
    active = sum(1 for l in cron_lines if any(w in l.lower() for w in ["active", "活跃", "enabled", "running"]))
    data["CRON_ACTIVE"] = str(active)
    data["CRON_FAILED_TEXT"] = ""
    items = []
    for line in cron_lines[:10]:
        items.append(f'<li><span class="cron-icon">⏱</span><span class="cron-name">{line[:50]}</span><span class="cron-status status-online">活跃</span></li>')
    data["CRON_LIST"] = "\n".join(items) if items else '<li><span class="cron-icon">—</span><span class="cron-name">暂无定时任务</span></li>'
    print(f"     总数: {data['CRON_TOTAL']} | 活跃: {data['CRON_ACTIVE']}")

    print("  4/6 host...")
    data.update(collect_host())
    print(f"     CPU: {data['CPU_USAGE']} | Mem: {data['MEM_GB']}GB ({data['MEM_USAGE']}) | Disk: {data['DISK_GB']}GB ({data['DISK_USAGE']})")

    print("  5/6 storage...")
    data.update(collect_storage())
    print(f"     Cache: {data['CACHE_SIZE']} | DB: {data['DB_SIZE']} | Memory: {data['MEMORY_COUNT']}")

    print("  6/6 cost...")
    data.update(collect_cost())

    print("📝 填充模板...")
    html = fill_template(data, date_str, weekday)

    index_path = os.path.join(REPORTS_DIR, "index.html")
    archive_path = os.path.join(REPORTS_DIR, f"{date_str}.html")

    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html)
    with open(archive_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ index.html ({len(html)} chars)")
    print(f"✅ {date_str}.html")

    # Git push
    os.chdir(REPORTS_DIR)
    run("git add index.html *.html 2>/dev/null")
    _, _, _ = run(f'git commit -m "日报 {date_str}" 2>/dev/null')
    push_out, push_err, push_rc = run("git push origin main 2>&1", timeout=30)
    if push_rc == 0:
        print("✅ 已推送 GitHub Pages")
    else:
        print(f"⚠️ git push 失败: {push_err[:200] if push_err else 'unknown'}")

    link = "https://burkereiii.github.io/hermes-daily-report/"
    print(f"\n🔗 {link}")
    return html


if __name__ == "__main__":
    main()
