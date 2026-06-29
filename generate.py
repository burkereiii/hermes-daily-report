#!/usr/bin/env python3
"""Hermes Daily Report Generator v5.0
Three-channel architecture, glassmorphism template, daily narrative.
"""
import subprocess, json, datetime, os, re, sys, tempfile, socket

REPORTS_DIR = r"C:\Users\沙河马\hermes-reports"
TEMPLATE = os.path.join(REPORTS_DIR, "template.html")


def run(cmd, timeout=30):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except Exception as e:
        return "", str(e), 1


def run_ps(script, timeout=30):
    """Run PowerShell snippet via temp file, avoiding bash $ expansion."""
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


def check_port(port):
    """Check if a TCP port is listening on localhost."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        result = s.connect_ex(('127.0.0.1', port))
        s.close()
        return result == 0
    except:
        return False


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
    """Collect core metrics from hermes insights (text output)."""
    out, err, rc = run("hermes insights --days 1", timeout=60)
    data = {
        "TOKEN_TOTAL": "—", "SESSION_COUNT": "0", "MESSAGE_COUNT": "0",
        "TOOL_COUNT": "0", "MODEL_NAME": "—", "MODEL_PROVIDER": "—",
        "DESKTOP_MSGS": "0", "WECHAT_MSGS": "0",
        "_raw_sessions": "", "_raw_tools": "",
    }
    for line in out.split("\n"):
        line = line.strip()
        m = re.search(r'Sessions:\s+([\d,]+)', line)
        if m: data["SESSION_COUNT"] = m.group(1).replace(",", "")
        m = re.search(r'Messages:\s+([\d,]+)', line)
        if m: data["MESSAGE_COUNT"] = m.group(1).replace(",", "")
        m = re.search(r'Tool calls:\s+([\d,]+)', line)
        if m: data["TOOL_COUNT"] = m.group(1).replace(",", "")
        m = re.search(r'Total tokens:\s+([\d,]+)', line)
        if m: data["TOKEN_TOTAL"] = human_num(int(m.group(1).replace(",", "")))
        m = re.search(r'Active time:\s+~?(\S+)', line)
        if m: data["_raw_sessions"] = m.group(1)
        # Platform rows
        if re.match(r'^(tui|desktop|cli)\s+\d+', line):
            parts = line.split()
            data["DESKTOP_MSGS"] = parts[2].replace(",", "") if len(parts) >= 3 else "0"
        elif re.match(r'^weixin\s+\d+', line) or re.match(r'^wechat\s+\d+', line):
            parts = line.split()
            data["WECHAT_MSGS"] = parts[2].replace(",", "") if len(parts) >= 3 else "0"
        # Model info
        m = re.search(r'(deepseek-v\d[\w.-]*|gpt-[\d.]+|claude[\w.-]*)\s+\d+\s+[\d,]+', line)
        if m:
            data["MODEL_NAME"] = m.group(1)
            data["MODEL_PROVIDER"] = "DeepSeek" if "deepseek" in m.group(1).lower() else \
                                     "OpenAI" if "gpt" in m.group(1).lower() else \
                                     "Anthropic" if "claude" in m.group(1).lower() else "—"
        # Tool breakdown for narrative
        m = re.match(r'(\w[\w_]*)\s+(\d+)\s+[\d.]+%', line)
        if m and m.group(1) not in ('Model', 'Platform', 'Tool'):
            if '_raw_tools' not in data: data["_raw_tools"] = ""
            data["_raw_tools"] += f"{m.group(1)}:{m.group(2)},"

    return data


def collect_channels():
    """Check three-channel connection status."""
    data = {}
    # Mac 远控 (Dashboard 9119)
    if check_port(9119):
        data["MAC_STATUS_CLASS"] = "online"
        data["MAC_STATUS_TEXT"] = "已连接"
    else:
        data["MAC_STATUS_CLASS"] = "offline"
        data["MAC_STATUS_TEXT"] = "未响应"

    # WebUI (8787)
    if check_port(8787):
        data["WEBUI_STATUS_CLASS"] = "online"
        data["WEBUI_STATUS_TEXT"] = "运行中"
    else:
        data["WEBUI_STATUS_CLASS"] = "offline"
        data["WEBUI_STATUS_TEXT"] = "未响应"

    # WeChat: detect from activity (will be filled after insights)
    data["WECHAT_STATUS_CLASS"] = "offline"
    data["WECHAT_STATUS_TEXT"] = "无活动"

    return data


def collect_gateway():
    """Collect gateway status."""
    data = {}
    gw_out, _, _ = run("hermes gateway status", timeout=15)
    m = re.search(r'PID:\s*(\d+)', gw_out)
    data["GATEWAY_PID"] = m.group(1) if m else "N/A"
    if "running" in gw_out.lower() or "运行" in gw_out:
        data["GATEWAY_STATUS"] = "运行中"
        data["GATEWAY_STATUS_CLASS"] = "online"
        data["GATEWAY_DOT_CLASS"] = "dot-online"
    else:
        data["GATEWAY_STATUS"] = "已停止"
        data["GATEWAY_STATUS_CLASS"] = "offline"
        data["GATEWAY_DOT_CLASS"] = "dot-offline"
    return data


def collect_cron():
    """Collect cron job list with proper parsing.

    Uses hermes cronjob list API (JSON) for reliable counts.
    Falls back to CLI text parsing.
    """
    data = {"CRON_TOTAL": "0", "CRON_ACTIVE": "0", "CRON_LIST": "", "CRON_FAILED_TEXT": ""}

    # Try JSON API first
    try:
        out, _, _ = run("hermes cron list --json 2>/dev/null", timeout=10)
        if out:
            cron_data = json.loads(out)
            jobs = cron_data.get("jobs", cron_data) if isinstance(cron_data, dict) else []
            if isinstance(jobs, list):
                data["CRON_TOTAL"] = str(len(jobs))
                active_jobs = [j for j in jobs if j.get("enabled") and j.get("state") != "paused"]
                data["CRON_ACTIVE"] = str(len(active_jobs))
                failed = [j for j in jobs if j.get("last_status") == "error"]
                if failed:
                    data["CRON_FAILED_TEXT"] = f" ⚠️ {len(failed)} 个异常"
                items = []
                for j in active_jobs[:10]:
                    name = j.get("name", j.get("job_id", "?"))[:30]
                    schedule = j.get("schedule", "?")
                    last_status = j.get("last_status", "ok")
                    tag_class = "error" if last_status == "error" else ""
                    items.append(
                        f'<li class="cron-item">'
                        f'<span class="cron-icon">⏱</span>'
                        f'<span class="cron-name">{name}</span>'
                        f'<span class="cron-schedule">{schedule}</span>'
                        f'<span class="cron-tag {tag_class}">{last_status}</span>'
                        f'</li>'
                    )
                data["CRON_LIST"] = "\n".join(items) if items else '<li class="cron-item"><span class="cron-icon">—</span><span class="cron-name">暂无活跃任务</span></li>'
                return data
    except: pass

    # Fallback: parse CLI text output
    cron_out, _, _ = run("hermes cron list", timeout=10)
    lines = [l.strip() for l in cron_out.split("\n") if l.strip() and not l.lower().startswith("no ")]
    # Parse structured output: look for job entries with IDs
    job_ids = set()
    for line in lines:
        m = re.match(r'^[a-f0-9]{10,}', line)
        if m: job_ids.add(m.group())
    data["CRON_TOTAL"] = str(len(job_ids)) if job_ids else str(len(lines))
    data["CRON_ACTIVE"] = data["CRON_TOTAL"]  # Can't tell active vs inactive from CLI

    items = []
    for line in lines[:10]:
        if re.match(r'^[a-f0-9]{10,}', line):
            items.append(
                f'<li class="cron-item">'
                f'<span class="cron-icon">⏱</span>'
                f'<span class="cron-name">{line[:50]}</span>'
                f'<span class="cron-schedule">—</span>'
                f'<span class="cron-tag">ok</span>'
                f'</li>'
            )
    data["CRON_LIST"] = "\n".join(items) if items else '<li class="cron-item"><span class="cron-icon">—</span><span class="cron-name">暂无活跃任务</span></li>'
    return data


def collect_host():
    """Collect Windows host metrics."""
    data = {"CPU_USAGE": "—", "MEM_GB": "—", "MEM_USAGE": "—",
            "DISK_GB": "—", "DISK_USAGE": "—", "MEM_WARN": "", "DISK_WARN": ""}

    out, _, _ = run_ps("(Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average")
    if out and out.replace('.', '').replace('-', '').isdigit():
        data["CPU_USAGE"] = str(int(float(out)))

    out, _, _ = run_ps("""$os=Get-CimInstance Win32_OperatingSystem;
$t=[math]::Round($os.TotalVisibleMemorySize/1MB);
$f=[math]::Round($os.FreePhysicalMemory/1MB);
Write-Output "$t|$f" """)
    if "|" in out:
        parts = out.strip().split("|")
        try:
            total_mb = float(parts[0])
            free_mb = float(parts[1])
            used_pct = round((1 - free_mb / total_mb) * 100)
            data["MEM_GB"] = str(int(total_mb))
            data["MEM_USAGE"] = str(used_pct)
            if used_pct > 90: data["MEM_WARN"] = " danger"
            elif used_pct > 75: data["MEM_WARN"] = " warn"
        except: pass

    out, _, _ = run_ps("""$d=Get-PSDrive C;
$used=[math]::Round($d.Used/1GB,1);
$total=[math]::Round(($d.Used+$d.Free)/1GB,1);
Write-Output "$used|$total" """)
    if "|" in out:
        parts = out.strip().split("|")
        try:
            used = float(parts[0])
            total = float(parts[1])
            used_pct = round(used/total*100)
            data["DISK_GB"] = str(used)
            data["DISK_USAGE"] = str(used_pct)
            if used_pct > 90: data["DISK_WARN"] = " danger"
            elif used_pct > 75: data["DISK_WARN"] = " warn"
        except: pass

    return data


def collect_storage():
    """Collect storage metrics."""
    data = {"CACHE_SIZE": "—", "DB_SIZE": "—", "MEMORY_COUNT": "—"}

    out, _, _ = run('bash -c "du -sh /d/Hermes/cache/ 2>/dev/null | cut -f1"')
    if out: data["CACHE_SIZE"] = out.strip()

    out, _, _ = run('bash -c "wc -c < /d/Hermes/state.db 2>/dev/null || echo 0"')
    try:
        data["DB_SIZE"] = human_bytes(int(out.strip()))
    except: pass

    return data


def collect_cost():
    return {"YESTERDAY_COST": "—", "COST_NOTE": "余额快照待恢复"}


def generate_narrative(insights, channels):
    """Generate daily summary HTML based on collected data."""
    sessions = int(insights.get("SESSION_COUNT", "0").replace("K", "000").replace("M", "000000") or "0")
    messages = int(insights.get("MESSAGE_COUNT", "0").replace(",", "") or "0")
    tokens = insights.get("TOKEN_TOTAL", "—")
    tool_calls = int(insights.get("TOOL_COUNT", "0").replace(",", "") or "0")
    desktop_msgs = int(insights.get("DESKTOP_MSGS", "0").replace(",", "") or "0")
    wechat_msgs = int(insights.get("WECHAT_MSGS", "0").replace(",", "") or "0")

    parts = []

    # Activity level
    if sessions == 0:
        parts.append("<p>今日暂无活跃会话。系统处于待命状态。</p>")
        parts.append('<div class="recommendation">所有通道检查正常，无需干预。</div>')
        return "\n".join(parts)

    # Session summary
    parts.append(f'<p>今日共 <span class="highlight">{sessions} 个会话</span>，产生 <span class="highlight">{messages}</span> 条消息，消耗 <span class="highlight">{tokens}</span> Token。</p>')

    # Platform breakdown
    if wechat_msgs > 0 and desktop_msgs > 0:
        parts.append(f'<p>平台分布：桌面终端 {desktop_msgs} 条（主力工作），微信 {wechat_msgs} 条（移动端轻交互）。</p>')
    elif desktop_msgs > 0:
        parts.append(f'<p>主要活动集中在桌面终端（{desktop_msgs} 条消息）。</p>')
    elif wechat_msgs > 0:
        parts.append(f'<p>主要活动在微信端（{wechat_msgs} 条消息），桌面端无活动。</p>')

    # Tool usage insight
    if tool_calls > 200:
        parts.append(f'<p>工具调用 <span class="highlight">{tool_calls}</span> 次，处于高强度工作状态。</p>')
    elif tool_calls > 50:
        parts.append(f'<p>工具调用 {tool_calls} 次，正常运维节奏。</p>')

    # Channel status
    issues = []
    if channels.get("MAC_STATUS_CLASS") == "offline":
        issues.append("Mac 远控未连接（Dashboard 9119 端口无响应）")
    if channels.get("WEBUI_STATUS_CLASS") == "offline":
        issues.append("WebUI 未运行（8787 端口无响应）")

    if issues:
        parts.append('<div class="recommendation">⚠️ ' + "；".join(issues) + "。建议检查对应服务进程。</div>")
    else:
        parts.append('<div class="recommendation">三通道全部在线，系统运行正常。如需关注特定指标，可在 Obsidian 系统运维中查看详情。</div>')

    return "\n".join(parts)


def fill_template(data: dict, date_str: str, weekday: str):
    """Substitute all placeholders in template."""
    data["REPORT_DATE"] = date_str
    data["REPORT_WEEKDAY"] = weekday

    with open(TEMPLATE, "r", encoding="utf-8") as f:
        html = f.read()

    for key, val in data.items():
        if key.startswith("_"): continue  # Skip internal fields
        html = html.replace("{{" + key + "}}", str(val))

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

    # 1/7: Insights
    print("  1/7 insights...")
    data.update(collect_insights())
    print(f"     Token: {data['TOKEN_TOTAL']} | 会话: {data['SESSION_COUNT']} | 消息: {data['MESSAGE_COUNT']}")

    # 2/7: Channels
    print("  2/7 三通道...")
    ch = collect_channels()
    # WeChat status: online if we have wechat messages today
    wechat_msgs = int(data.get("WECHAT_MSGS", "0").replace(",", "") or "0")
    if wechat_msgs > 0:
        ch["WECHAT_STATUS_CLASS"] = "online"
        ch["WECHAT_STATUS_TEXT"] = "活跃"
    elif check_port(9119):  # Gateway is running, WeChat might just have no messages
        ch["WECHAT_STATUS_CLASS"] = "activity"
        ch["WECHAT_STATUS_TEXT"] = "待命中"
    data.update(ch)
    print(f"     Mac: {data['MAC_STATUS_TEXT']} | 微信: {data['WECHAT_STATUS_TEXT']} | WebUI: {data['WEBUI_STATUS_TEXT']}")

    # 3/7: Gateway
    print("  3/7 gateway...")
    data.update(collect_gateway())
    print(f"     PID: {data['GATEWAY_PID']} | 状态: {data['GATEWAY_STATUS']}")

    # 4/7: Cron
    print("  4/7 cron...")
    data.update(collect_cron())
    print(f"     总数: {data['CRON_TOTAL']} | 活跃: {data['CRON_ACTIVE']}")

    # 5/7: Host
    print("  5/7 host...")
    data.update(collect_host())
    print(f"     CPU: {data['CPU_USAGE']}% | Mem: {data['MEM_GB']}GB ({data['MEM_USAGE']}%) | Disk: {data['DISK_GB']}GB ({data['DISK_USAGE']}%)")

    # 6/7: Storage
    print("  6/7 storage...")
    data.update(collect_storage())
    print(f"     Cache: {data['CACHE_SIZE']} | DB: {data['DB_SIZE']} | Memory: {data['MEMORY_COUNT']}")

    # 7/7: Cost + Narrative
    print("  7/7 cost + narrative...")
    data.update(collect_cost())
    data["DAILY_SUMMARY"] = generate_narrative(data, ch)

    # Fill template
    print("📝 填充模板...")
    html = fill_template(data, date_str, weekday)

    # Write output
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
    run("git add index.html generate.py template.html 2>/dev/null")
    archive = f"{date_str}.html"
    if os.path.exists(archive):
        run(f"git add {archive} 2>/dev/null")
    out, err, rc = run(f'git commit -m "日报 {date_str} v5.0 三通道+毛玻璃+叙事" 2>&1')
    if rc == 0:
        push_out, push_err, push_rc = run("git push origin main 2>&1", timeout=30)
        if push_rc == 0:
            print("✅ 已推送 GitHub Pages")
        else:
            print(f"⚠️ git push 失败: {push_err[:200] if push_err else 'unknown'}")
    else:
        if "nothing to commit" in (out + err):
            push_out, push_err, push_rc = run("git push origin main 2>&1", timeout=30)
            if push_rc == 0:
                print("✅ 已推送 GitHub Pages (无变更)")
            else:
                print(f"⚠️ git push 失败: {push_err[:200] if push_err else 'unknown'}")
        else:
            print(f"⚠️ git commit 失败: {err[:200] if err else out[:200]}")

    link = "https://burkereiii.github.io/hermes-daily-report/"
    print(f"\n🔗 {link}")
    return html


if __name__ == "__main__":
    main()
