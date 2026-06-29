#!/usr/bin/env python3
"""Hermes Daily Report Generator v6.0
Oliver-inspired design, full insights parsing, rich data cards.
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


def parse_insights_full(out):
    """Parse all fields from hermes insights text output. Returns a dict."""
    d = {}
    # Defaults
    d["SESSION_COUNT"] = "0"
    d["MESSAGE_COUNT"] = "0"
    d["TOOL_COUNT"] = "0"
    d["TOKEN_TOTAL"] = "—"
    d["INPUT_TOKENS"] = "—"
    d["OUTPUT_TOKENS"] = "—"
    d["USER_MESSAGES"] = "0"
    d["ACTIVE_TIME"] = "—"
    d["AVG_SESSION"] = "—"
    d["MODEL_NAME"] = "—"
    d["MODEL_PROVIDER"] = "—"
    d["MODEL_STABILITY"] = ""
    d["DESKTOP_MSGS"] = "0"
    d["WECHAT_MSGS"] = "0"
    d["PEAK_HOURS"] = "—"
    d["WEEK_COUNTS"] = [0]*7  # Mon-Sun
    d["_tools"] = []   # [(name, count, pct), ...]
    d["_skills"] = []  # [(name, loads, edits), ...]
    d["_notable"] = [] # [(icon, label, value, session_id), ...]

    section = None
    lines = out.split("\n")

    for line in lines:
        s = line.strip()
        if not s: continue

        # Detect sections
        if "📋 Overview" in s: section = "overview"; continue
        if "🤖 Models Used" in s: section = "models"; continue
        if "📱 Platforms" in s: section = "platforms"; continue
        if "🔧 Top Tools" in s: section = "tools"; continue
        if "🧠 Top Skills" in s: section = "skills"; continue
        if "📅 Activity Patterns" in s: section = "activity"; continue
        if "🏆 Notable Sessions" in s: section = "notable"; continue

        if section == "overview":
            m = re.search(r'Sessions:\s+([\d,]+)', s); 
            if m: d["SESSION_COUNT"] = m.group(1).replace(",", "")
            m = re.search(r'Messages:\s+([\d,]+)', s)
            if m: d["MESSAGE_COUNT"] = m.group(1).replace(",", "")
            m = re.search(r'Tool calls:\s+([\d,]+)', s)
            if m: d["TOOL_COUNT"] = m.group(1).replace(",", "")
            m = re.search(r'User messages:\s+([\d,]+)', s)
            if m: d["USER_MESSAGES"] = m.group(1).replace(",", "")
            m = re.search(r'Input tokens:\s+([\d,]+)', s)
            if m: d["INPUT_TOKENS"] = human_num(int(m.group(1).replace(",", "")))
            m = re.search(r'Output tokens:\s+([\d,]+)', s)
            if m: d["OUTPUT_TOKENS"] = human_num(int(m.group(1).replace(",", "")))
            m = re.search(r'Total tokens:\s+([\d,]+)', s)
            if m: d["TOKEN_TOTAL"] = human_num(int(m.group(1).replace(",", "")))
            m = re.search(r'Active time:\s+~?(\S+)', s)
            if m: d["ACTIVE_TIME"] = m.group(1)
            m = re.search(r'Avg session:\s+~?(\S+)', s)
            if m: d["AVG_SESSION"] = m.group(1)

        elif section == "models":
            m = re.search(r'^(deepseek-v\d[\w.-]*|gpt-[\d.]+|claude[\w.-]*)\s+(\d+)\s+[\d,]+', s)
            if m:
                d["MODEL_NAME"] = m.group(1)
                sessions = int(m.group(2))
                if "deepseek" in m.group(1).lower():
                    d["MODEL_PROVIDER"] = "DeepSeek"
                elif "gpt" in m.group(1).lower():
                    d["MODEL_PROVIDER"] = "OpenAI"
                elif "claude" in m.group(1).lower():
                    d["MODEL_PROVIDER"] = "Anthropic"
                d["MODEL_STABILITY"] = " · 单模型 · 无 fallback"

        elif section == "platforms":
            if re.match(r'^(tui|desktop|cli)\s+\d+', s):
                parts = s.split()
                d["DESKTOP_MSGS"] = parts[2].replace(",", "") if len(parts) >= 3 else "0"
            elif re.match(r'^weixin\s+\d+', s) or re.match(r'^wechat\s+\d+', s):
                parts = s.split()
                d["WECHAT_MSGS"] = parts[2].replace(",", "") if len(parts) >= 3 else "0"

        elif section == "tools":
            m = re.match(r'^(\w[\w_]*)\s+([\d,]+)\s+([\d.]+)%', s)
            if m:
                name = m.group(1)
                count = int(m.group(2).replace(",", ""))
                pct = float(m.group(3))
                if name not in ('Model', 'Platform', 'Tool', '...'):
                    d["_tools"].append((name, count, pct))

        elif section == "skills":
            m = re.match(r'^(\S[\S ]*?)\s+(\d+)\s+(\d+)\s+', s)
            if m:
                name = m.group(1).strip()
                loads = int(m.group(2))
                edits = int(m.group(3))
                if name not in ('Skill', 'Distinct'):
                    d["_skills"].append((name, loads, edits))

        elif section == "activity":
            if "Peak hours:" in s:
                m = re.search(r'Peak hours:\s*(.+)', s)
                if m: d["PEAK_HOURS"] = m.group(1).strip()
            # Week day bars: "Mon  ███████████████ 7"
            day_map = {'Mon':0,'Tue':1,'Wed':2,'Thu':3,'Fri':4,'Sat':5,'Sun':6}
            m = re.match(r'^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+\S+\s+(\d+)', s)
            if m:
                idx = day_map.get(m.group(1), -1)
                if idx >= 0:
                    d["WEEK_COUNTS"][idx] = int(m.group(2))

        elif section == "notable":
            m = re.match(r'^(Longest session|Most messages|Most tokens|Most tool calls)\s+(.+?)\s+\((.+)\)', s)
            if m:
                label = m.group(1)
                value = m.group(2).strip()
                sid = m.group(3).strip()
                icon_map = {
                    'Longest session': '⏳', 'Most messages': '💬',
                    'Most tokens': '⚡', 'Most tool calls': '🔧'
                }
                d["_notable"].append((icon_map.get(label, '📌'), label, value, sid))

    return d


def generate_top_tools(tools):
    """Generate HTML for top tools ranking."""
    if not tools:
        return '<li class="rank-item"><span class="rank-name">暂无数据</span></li>'
    max_count = max(c for _, c, _ in tools) if tools else 1
    items = []
    for i, (name, count, pct) in enumerate(tools[:10]):
        bar_w = int(count / max_count * 100)
        items.append(
            f'<li class="rank-item">'
            f'<span class="rank-pos">{i+1:02d}</span>'
            f'<span class="rank-name">{name}</span>'
            f'<div class="rank-bar-wrap"><div class="rank-bar" style="width:{bar_w}%"></div></div>'
            f'<span class="rank-count">{count}</span>'
            f'</li>'
        )
    return "\n".join(items)


def generate_top_skills(skills):
    """Generate HTML for top skills list."""
    if not skills:
        return '<li class="rank-item"><span class="rank-name">暂无数据</span></li>'
    items = []
    for i, (name, loads, edits) in enumerate(skills[:10]):
        items.append(
            f'<li class="rank-item">'
            f'<span class="rank-pos">{i+1:02d}</span>'
            f'<span class="rank-name">{name}</span>'
            f'<span class="rank-count">加载 {loads} · 编辑 {edits}</span>'
            f'</li>'
        )
    return "\n".join(items)


def generate_week_bars(counts):
    """Generate HTML divs for weekly activity chart."""
    max_c = max(counts) if counts and max(counts) > 0 else 1
    bars = []
    for c in counts:
        h = max(3, int(c / max_c * 76))
        cls = 'week-bar' if c > 0 else 'week-bar inactive'
        bars.append(f'<div class="{cls}" style="height:{h}px" title="{c} 会话"></div>')
    return "\n".join(bars)


def generate_notable_sessions(notable):
    """Generate HTML cards for notable sessions."""
    if not notable:
        return '<div class="notable-card"><div class="notable-value">—</div><div class="notable-label">暂无数据</div></div>'
    cards = []
    for icon, label, value, sid in notable[:3]:
        # Truncate session ID
        short_sid = sid[:30] + "…" if len(sid) > 30 else sid
        cards.append(
            f'<div class="notable-card">'
            f'<div class="notable-icon">{icon}</div>'
            f'<div class="notable-label">{label}</div>'
            f'<div class="notable-value">{value}</div>'
            f'<div class="notable-session">{short_sid}</div>'
            f'</div>'
        )
    return "\n".join(cards)


def collect_channels():
    data = {}
    if check_port(9119):
        data["MAC_STATUS_CLASS"] = "online"; data["MAC_STATUS_TEXT"] = "已连接"
    else:
        data["MAC_STATUS_CLASS"] = "offline"; data["MAC_STATUS_TEXT"] = "未响应"
    if check_port(8787):
        data["WEBUI_STATUS_CLASS"] = "online"; data["WEBUI_STATUS_TEXT"] = "运行中"
    else:
        data["WEBUI_STATUS_CLASS"] = "offline"; data["WEBUI_STATUS_TEXT"] = "未响应"
    data["WECHAT_STATUS_CLASS"] = "offline"; data["WECHAT_STATUS_TEXT"] = "无活动"
    return data


def collect_gateway():
    data = {}
    gw_out, _, _ = run("hermes gateway status", timeout=15)
    m = re.search(r'PID:\s*(\d+)', gw_out)
    data["GATEWAY_PID"] = m.group(1) if m else "N/A"
    data["GATEWAY_STATUS"] = "运行中" if ("running" in gw_out.lower() or "运行" in gw_out) else "已停止"
    return data


def collect_cron():
    data = {"CRON_TOTAL": "0", "CRON_ACTIVE": "0", "CRON_LIST": "", "CRON_FAILED_TEXT": ""}
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
                if failed: data["CRON_FAILED_TEXT"] = f"⚠️ {len(failed)} 异常"
                items = []
                for j in active_jobs[:10]:
                    name = j.get("name", j.get("job_id", "?"))[:35]
                    schedule = j.get("schedule", "?")
                    status = j.get("last_status", "ok")
                    tag = '<span style="color:var(--red);">error</span>' if status == "error" else '<span style="color:var(--green-dim);">ok</span>'
                    items.append(
                        f'<li class="rank-item">'
                        f'<span class="rank-pos">⏱</span>'
                        f'<span class="rank-name">{name}</span>'
                        f'<span class="rank-count">{schedule}</span>'
                        f'<span class="rank-count">{tag}</span>'
                        f'</li>'
                    )
                data["CRON_LIST"] = "\n".join(items) if items else '<li class="rank-item"><span class="rank-name">暂无活跃任务</span></li>'
                return data
    except: pass

    cron_out, _, _ = run("hermes cron list", timeout=10)
    lines = [l.strip() for l in cron_out.split("\n") if l.strip()]
    job_ids = set()
    for line in lines:
        m = re.match(r'^[a-f0-9]{10,}', line)
        if m: job_ids.add(m.group())
    data["CRON_TOTAL"] = str(len(job_ids)) if job_ids else "1"
    data["CRON_ACTIVE"] = data["CRON_TOTAL"]
    items = []
    for line in lines:
        if re.match(r'^[a-f0-9]{10,}', line):
            items.append(
                f'<li class="rank-item">'
                f'<span class="rank-pos">⏱</span>'
                f'<span class="rank-name">{line[:35]}</span>'
                f'<span class="rank-count"><span style="color:var(--green-dim);">ok</span></span>'
                f'</li>'
            )
    data["CRON_LIST"] = "\n".join(items) if items else '<li class="rank-item"><span class="rank-name">暂无活跃任务</span></li>'
    return data


def collect_host():
    data = {"CPU_USAGE": "—", "MEM_GB": "—", "MEM_USAGE": "—",
            "DISK_GB": "—", "DISK_USAGE": "—", "MEM_WARN": "", "DISK_WARN": ""}
    out, _, _ = run_ps("(Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average")
    if out and out.replace('.','').replace('-','').isdigit():
        data["CPU_USAGE"] = str(int(float(out)))
    out, _, _ = run_ps("$os=Get-CimInstance Win32_OperatingSystem;$t=[math]::Round($os.TotalVisibleMemorySize/1MB);$f=[math]::Round($os.FreePhysicalMemory/1MB);Write-Output \"$t|$f\"")
    if "|" in out:
        parts = out.strip().split("|")
        try:
            t, f = float(parts[0]), float(parts[1])
            pct = round((1-f/t)*100)
            data["MEM_GB"] = str(int(t)); data["MEM_USAGE"] = str(pct)
            if pct > 90: data["MEM_WARN"] = " danger"
            elif pct > 75: data["MEM_WARN"] = " warn"
        except: pass
    out, _, _ = run_ps("$d=Get-PSDrive C;$u=[math]::Round($d.Used/1GB,1);$t=[math]::Round(($d.Used+$d.Free)/1GB,1);Write-Output \"$u|$t\"")
    if "|" in out:
        parts = out.strip().split("|")
        try:
            u, t = float(parts[0]), float(parts[1])
            pct = round(u/t*100)
            data["DISK_GB"] = str(u); data["DISK_USAGE"] = str(pct)
            if pct > 90: data["DISK_WARN"] = " danger"
            elif pct > 75: data["DISK_WARN"] = " warn"
        except: pass
    return data


def collect_storage():
    data = {"CACHE_SIZE": "—", "DB_SIZE": "—", "MEMORY_COUNT": "—"}
    out, _, _ = run('bash -c "du -sh /d/Hermes/cache/ 2>/dev/null | cut -f1"')
    if out: data["CACHE_SIZE"] = out.strip()
    out, _, _ = run('bash -c "wc -c < /d/Hermes/state.db 2>/dev/null || echo 0"')
    try: data["DB_SIZE"] = human_bytes(int(out.strip()))
    except: pass
    return data


def collect_cost():
    return {"YESTERDAY_COST": "—", "COST_NOTE": "余额快照待恢复"}


def fill_template(data, date_str, weekday):
    data["REPORT_DATE"] = date_str
    data["REPORT_WEEKDAY"] = weekday
    with open(TEMPLATE, "r", encoding="utf-8") as f:
        html = f.read()
    for key, val in data.items():
        if key.startswith("_"): continue
        html = html.replace("{{" + key + "}}", str(val))
    remaining = re.findall(r'\{\{\s*(\w+)\s*\}\}', html)
    if remaining:
        print(f"⚠️ {len(remaining)} 个占位符未填充: {remaining}")
    return html


def main():
    today = datetime.date.today()
    date_str = today.strftime("%Y-%m-%d")
    weekdays = ["星期一","星期二","星期三","星期四","星期五","星期六","星期日"]
    weekday = weekdays[today.weekday()]
    print(f"📊 采集 {date_str} ({weekday}) …")

    # 1. Insights (all data)
    print("  1/5 insights (全字段解析) …")
    out, _, _ = run("hermes insights --days 1", timeout=60)
    data = parse_insights_full(out)
    print(f"     会话 {data['SESSION_COUNT']} · 消息 {data['MESSAGE_COUNT']} · Token {data['TOKEN_TOTAL']} · 工具 {data['TOOL_COUNT']}")

    # 2. Channels + Gateway
    print("  2/5 三通道 + 网关 …")
    ch = collect_channels()
    wechat_msgs = int(data.get("WECHAT_MSGS", "0").replace(",","") or "0")
    if wechat_msgs > 0:
        ch["WECHAT_STATUS_CLASS"] = "online"; ch["WECHAT_STATUS_TEXT"] = "活跃"
    elif check_port(9119):
        ch["WECHAT_STATUS_CLASS"] = "activity"; ch["WECHAT_STATUS_TEXT"] = "待命中"
    data.update(ch)
    data.update(collect_gateway())
    print(f"     Mac {data['MAC_STATUS_TEXT']} · 微信 {data['WECHAT_STATUS_TEXT']} · WebUI {data['WEBUI_STATUS_TEXT']}")

    # 3. Generate rich content
    print("  3/5 生成排行+图表 …")
    data["TOP_TOOLS"] = generate_top_tools(data["_tools"])
    data["TOP_SKILLS"] = generate_top_skills(data["_skills"])
    data["WEEK_BARS"] = generate_week_bars(data["WEEK_COUNTS"])
    data["NOTABLE_SESSIONS"] = generate_notable_sessions(data["_notable"])
    print(f"     工具 {len(data['_tools'])} 种 · 技能 {len(data['_skills'])} 种 · 亮点 {len(data['_notable'])} 项")

    # 4. Host + Storage + Cron + Cost
    print("  4/5 主机+存储+Cron …")
    data.update(collect_host())
    data.update(collect_storage())
    data.update(collect_cron())
    data.update(collect_cost())

    # 5. Narrative
    print("  5/5 生成叙事 …")
    sessions = data["SESSION_COUNT"]
    msgs = data["MESSAGE_COUNT"]
    tokens = data["TOKEN_TOTAL"]
    tools = data["TOOL_COUNT"]
    user_msgs = data.get("USER_MESSAGES", "0")
    active_t = data.get("ACTIVE_TIME", "—")

    summary_parts = []
    summary_parts.append(f'今日共 {sessions} 个会话，{msgs} 条消息（用户 {user_msgs} 条），活跃 {active_t}，消耗 {tokens} Token。')
    if data.get("_tools"):
        top3 = [t[0] for t in data["_tools"][:3]]
        summary_parts.append(f'主力工具：{", ".join(top3)}。')
    if data.get("_skills"):
        top_skills = [s[0] for s in data["_skills"][:3]]
        summary_parts.append(f'高频技能：{", ".join(top_skills)}。')

    data["DAILY_SUMMARY"] = " ".join(summary_parts)

    # Recommendation
    rec = "三通道全部在线，系统运行正常。"
    if data.get("MEM_WARN") == " danger":
        rec = "⚠️ 内存使用率过高，建议释放部分进程。"
    elif data.get("DISK_WARN") == " danger":
        rec = "⚠️ 磁盘使用率过高，建议清理。"
    elif int(data.get("TOOL_COUNT", "0").replace(",","") or "0") > 500:
        rec = "今日高强度工作，建议检查是否有冗余工具调用。"
    data["DAILY_RECOMMENDATION"] = rec

    # Fill + write
    print("📝 填充模板 …")
    html = fill_template(data, date_str, weekday)

    index_path = os.path.join(REPORTS_DIR, "index.html")
    archive_path = os.path.join(REPORTS_DIR, f"{date_str}.html")
    with open(index_path, "w", encoding="utf-8") as f: f.write(html)
    with open(archive_path, "w", encoding="utf-8") as f: f.write(html)
    print(f"✅ index.html ({len(html)} chars) · {date_str}.html")

    # Git
    os.chdir(REPORTS_DIR)
    run("git add index.html generate.py template.html 2>/dev/null")
    if os.path.exists(f"{date_str}.html"):
        run(f"git add {date_str}.html 2>/dev/null")
    out_c, err_c, rc_c = run(f'git commit -m "日报 {date_str} v6 Oliver风格+全字段" 2>&1')
    if rc_c == 0:
        _, _, rc_p = run("git push origin main 2>&1", timeout=30)
        print("✅ 已推送" if rc_p == 0 else "⚠️ push 失败")
    else:
        if "nothing to commit" in (out_c + err_c):
            _, _, rc_p = run("git push origin main 2>&1", timeout=30)
            print("✅ 已推送 (无变更)" if rc_p == 0 else "⚠️ push 失败")
        else:
            print(f"⚠️ commit: {err_c[:100]}")

    print(f"\n🔗 https://burkereiii.github.io/hermes-daily-report/")


if __name__ == "__main__":
    main()
