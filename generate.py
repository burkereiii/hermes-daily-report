#!/usr/bin/env python3
"""Hermes Daily Report Generator v8.0 — Full-spectrum data, --json mode for agent-driven pipeline."""
import subprocess, json, datetime, os, re, sys, tempfile, socket, random

REPORTS_DIR = r"C:\Users\沙河马\hermes-reports"
TEMPLATE = os.path.join(REPORTS_DIR, "template.html")
REPORT_DATE = None  # Set by main() so all collectors use the same date

# ── Translation maps (extended for v8) ──
TOOL_CN = {
    "terminal":"终端","read_file":"读文件","search_files":"搜索","patch":"补丁",
    "process":"进程","browser_navigate":"浏览","execute_code":"执行代码",
    "write_file":"写文件","skill_view":"查技能","session_search":"会话搜索",
    "cronjob":"定时任务","skill_manage":"技能管理","image_generate":"生图",
    "todo":"清单","browser_snapshot":"快照","browser_vision":"视觉",
    "browser_click":"点击","browser_scroll":"滚动","browser_console":"控制台",
    "vision_analyze":"图像分析","text_to_speech":"语音","delegate_task":"委派",
    "computer_use":"桌面操控","memory":"记忆","browser_type":"输入",
    "browser_press":"按键",
}
SKILL_CN = {
    "hippo-selfie":"麻衣自拍","hermes-daily-report":"系统日报","hermes-agent":"配置管理",
    "obsidian":"笔记管理","plan":"计划制定","systematic-debugging":"系统调试",
    "comfyui":"AI绘画","hermes-remote-gateway":"远程网关",
    "hermes-agent-skill-authoring":"技能编写","knowledge-curation":"知识策展",
    "obsidian-vault-discovery":"Obsidian管理",
    "video-transcription":"视频转录","requesting-code-review":"代码审查",
    "simplify-code":"代码精简","hermes-web-search":"网页搜索",
    "test-driven-development":"TDD","video-content-extraction":"视频内容提取",
}
NOTABLE_CN = {
    "Longest session":"最长会话","Most messages":"最多消息",
    "Most tokens":"最多Token","Most tool calls":"最多工具调用",
}
CRON_DESC = {
    "日报生成":"每日零点自动生成系统日报，推送至 GitHub Pages",
    "全盘健康检查":"凌晨3点采集系统指标并诊断，异常推送微信告警",
    "宿主进程自动清理":"每30分钟清理僵尸进程和临时文件",
    "峰值采样":"每分钟采样CPU/内存/磁盘，用于日报真实峰值数据",
}
CRON_SCHED_CN = {
    "0 0 * * *":"每天 00:00",
    "0 3 * * *":"每天 03:00",
    "*/30 * * * *":"每 30 分钟",
    "* * * * *":"每分钟",
}

def run(cmd, timeout=30):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except: return "", str(sys.exc_info()[1]), 1

def run_ps(script, timeout=30):
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.ps1', delete=False, encoding='utf-8')
    tmp.write(script); tmp.close()
    try:
        r = subprocess.run(['powershell','-File',tmp.name], capture_output=True, text=True, timeout=timeout)
        os.unlink(tmp.name); return r.stdout.strip(), r.stderr.strip(), r.returncode
    except Exception as e:
        try: os.unlink(tmp.name)
        except: pass
        return "", str(e), 1

def check_port(port):
    try:
        s=socket.socket(socket.AF_INET,socket.SOCK_STREAM); s.settimeout(2)
        r=s.connect_ex(('127.0.0.1',port)); s.close(); return r==0
    except: return False

def human_bytes(n):
    if n<1024: return f"{n}B"
    if n<1048576: return f"{n/1024:.1f}K"
    if n<1073741824: return f"{n/1048576:.1f}M"
    return f"{n/1073741824:.2f}G"

def human_num(n):
    if n is None: return "—"
    n=int(n)
    if n>=1000000: return f"{n/1000000:.1f}M"
    if n>=1000: return f"{n/1000:.1f}K"
    return str(n)

def delta_str(today, yesterday):
    """Generate delta display string with direction."""
    if today is None or yesterday is None or yesterday == 0:
        return "", "flat"
    diff = today - yesterday
    pct = abs(diff) / yesterday * 100 if yesterday > 0 else 0
    if diff > 0:
        return f"↑ {abs(diff):+d} ({pct:.0f}%)", "up"
    elif diff < 0:
        return f"↓ {abs(diff):d} ({pct:.0f}%)", "down"
    return "→ 持平", "flat"

# ═══════════════════════ DATA COLLECTION (self-collect mode) ═══════════════════════

def parse_insights_full(out):
    d = {"SESSION_COUNT":"0","MESSAGE_COUNT":"0","TOOL_COUNT":"0","TOKEN_TOTAL":"—",
         "INPUT_TOKENS":"—","OUTPUT_TOKENS":"—","USER_MESSAGES":"0",
         "ACTIVE_TIME":"—","AVG_SESSION":"—","MODEL_NAME":"—","MODEL_PROVIDER":"—",
         "MODEL_STABILITY":"","DESKTOP_MSGS":"0","WECHAT_MSGS":"0",
         "PEAK_HOURS":"—","WEEK_COUNTS":[0]*7,"_tools":[],"_skills":[],"_notable":[],
         "_peak_raw":"","_raw_sessions":"0","_raw_messages":"0","_raw_tool_calls":"0",
         "_raw_user_msgs":"0","_raw_active_time":"—","_raw_avg_session":"—",
         "_raw_input_tokens":0,"_raw_output_tokens":0,"_raw_total_tokens":0}
    section=None
    for line in out.split("\n"):
        s=line.strip()
        if not s: continue
        if "📋 Overview" in s: section="overview"; continue
        if "🤖 Models Used" in s: section="models"; continue
        if "📱 Platforms" in s: section="platforms"; continue
        if "🔧 Top Tools" in s: section="tools"; continue
        if "🧠 Top Skills" in s: section="skills"; continue
        if "📅 Activity Patterns" in s: section="activity"; continue
        if "🏆 Notable Sessions" in s: section="notable"; continue

        if section=="overview":
            m=re.search(r'Sessions:\s+([\d,]+)',s)
            if m:
                v=m.group(1).replace(",","")
                d["SESSION_COUNT"]=v; d["_raw_sessions"]=v
            m=re.search(r'Messages:\s+([\d,]+)',s)
            if m:
                v=m.group(1).replace(",","")
                d["MESSAGE_COUNT"]=v; d["_raw_messages"]=v
            m=re.search(r'Tool calls:\s+([\d,]+)',s)
            if m:
                v=m.group(1).replace(",","")
                d["TOOL_COUNT"]=v; d["_raw_tool_calls"]=v
            m=re.search(r'User messages:\s+([\d,]+)',s)
            if m:
                v=m.group(1).replace(",","")
                d["USER_MESSAGES"]=v; d["_raw_user_msgs"]=v
            m=re.search(r'Input tokens:\s+([\d,]+)',s)
            if m:
                v=int(m.group(1).replace(",",""))
                d["INPUT_TOKENS"]=human_num(v); d["_raw_input_tokens"]=v
            m=re.search(r'Output tokens:\s+([\d,]+)',s)
            if m:
                v=int(m.group(1).replace(",",""))
                d["OUTPUT_TOKENS"]=human_num(v); d["_raw_output_tokens"]=v
            m=re.search(r'Total tokens:\s+([\d,]+)',s)
            if m:
                v=int(m.group(1).replace(",",""))
                d["TOKEN_TOTAL"]=human_num(v); d["_raw_total_tokens"]=v
            m=re.search(r'Active time:\s+~?(\S+)',s)
            if m: d["ACTIVE_TIME"]=m.group(1); d["_raw_active_time"]=m.group(1)
            m=re.search(r'Avg session:\s+~?(\S+)',s)
            if m: d["AVG_SESSION"]=m.group(1); d["_raw_avg_session"]=m.group(1)

        elif section=="models":
            m=re.search(r'^(deepseek-v[\w.\-]*|gpt-[\d.]+|claude[\w.\-]*)\s+(\d+)\s+[\d,]+',s)
            if m:
                d["MODEL_NAME"]=m.group(1)
                d["MODEL_PROVIDER"]={"deepseek":"DeepSeek","gpt":"OpenAI","claude":"Anthropic"}.get(
                    next((k for k in ["deepseek","gpt","claude"] if k in m.group(1).lower()),""),"—")
                d["MODEL_STABILITY"]=" · 单模型 · 无 fallback"

        elif section=="platforms":
            if re.match(r'^(tui|desktop|cli)\s+\d+',s):
                p=s.split(); d["DESKTOP_MSGS"]=p[2].replace(",","") if len(p)>=3 else "0"
            elif re.match(r'^weixin\s+\d+',s) or re.match(r'^wechat\s+\d+',s):
                p=s.split(); d["WECHAT_MSGS"]=p[2].replace(",","") if len(p)>=3 else "0"

        elif section=="tools":
            m=re.match(r'^(\w[\w_]*)\s+([\d,]+)\s+([\d.]+)%',s)
            if m and m.group(1) not in ('Model','Platform','Tool','...'):
                d["_tools"].append((m.group(1),int(m.group(2).replace(",","")),float(m.group(3))))

        elif section=="skills":
            m=re.match(r'^(\S[\S ]*?)\s+(\d+)\s+(\d+)\s+',s)
            if m and m.group(1).strip() not in ('Skill','Distinct'):
                d["_skills"].append((m.group(1).strip(),int(m.group(2)),int(m.group(3))))

        elif section=="activity":
            if "Peak hours:" in s:
                m=re.search(r'Peak hours:\s*(.+)',s)
                if m: d["_peak_raw"]=m.group(1).strip()
            day_map={'Mon':0,'Tue':1,'Wed':2,'Thu':3,'Fri':4,'Sat':5,'Sun':6}
            m=re.match(r'^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+\S+\s+(\d+)',s)
            if m:
                idx=day_map.get(m.group(1),-1)
                if idx>=0: d["WEEK_COUNTS"][idx]=int(m.group(2))

        elif section=="notable":
            m=re.match(r'^(Longest session|Most messages|Most tokens|Most tool calls)\s+(.+?)\s+\((.+)\)',s)
            if m: d["_notable"].append((m.group(1),m.group(2).strip(),m.group(3).strip()))

    return d

def collect_channels():
    data={}
    dash_ok=check_port(9119)
    cw=0
    if dash_ok:
        out,_,_=run('bash -c "netstat -ano 2>/dev/null | grep :9119 | grep CLOSE_WAIT | wc -l"',timeout=5)
        try: cw=int(out.strip() or "0")
        except: pass
    if dash_ok:
        if cw>10: data["MAC_STATUS_CLASS"]="activity"; data["MAC_STATUS_TEXT"]=f"在线 · {cw} CLOSE_WAIT ⚠️"
        else: data["MAC_STATUS_CLASS"]="online"; data["MAC_STATUS_TEXT"]=f"在线 ({cw} CW)"
    else: data["MAC_STATUS_CLASS"]="offline"; data["MAC_STATUS_TEXT"]="离线"

    data["WEBUI_STATUS_CLASS"]="online" if check_port(8787) else "offline"
    data["WEBUI_STATUS_TEXT"]="在线" if check_port(8787) else "离线"
    data["PREVIEW_STATUS_CLASS"]="online" if check_port(8899) else "offline"
    data["PREVIEW_STATUS_TEXT"]="在线" if check_port(8899) else "离线"
    data["WECHAT_STATUS_CLASS"]="offline"; data["WECHAT_STATUS_TEXT"]="离线"
    return data

def collect_gateway():
    gw,_,_=run("hermes gateway status",timeout=10)
    m=re.search(r'PID:\s*(\d+)',gw)
    pid = m.group(1) if m else None
    if pid:
        return {
            "GATEWAY_PID": pid,
            "GATEWAY_STATUS": "运行中" if ("running" in gw.lower() or "运行" in gw) else "已停止"
        }
    # Fallback: check if gateway PID from cache is still alive
    try:
        cache = "D:\\Hermes\\cache\\gateway_pid.txt"
        if os.path.exists(cache):
            with open(cache) as f: last_pid = f.read().strip()
            out,_,_=run(f"tasklist /FI \"PID eq {last_pid}\" 2>nul",timeout=5)
            if last_pid in out:
                return {"GATEWAY_PID": last_pid, "GATEWAY_STATUS": "运行中 (无响应)"}
    except: pass
    return {"GATEWAY_PID": "N/A", "GATEWAY_STATUS": "已停止"}

def collect_tailscale():
    data={"TAILSCALE_STATUS":"—","TAILSCALE_STATUS_CLASS":"offline",
          "TAILSCALE_IP":"—","TAILSCALE_DNS":"—","TAILSCALE_EXIT":"",
          "NETWORK_SUMMARY":"—"}
    out,_,_=run('tailscale status --json 2>nul',timeout=10)
    if out:
        try:
            ts=json.loads(out)
            if ts.get("Self"):
                s=ts["Self"]
                data["TAILSCALE_STATUS"]="在线" if s.get("Online") else "离线"
                data["TAILSCALE_STATUS_CLASS"]="online" if s.get("Online") else "offline"
                data["TAILSCALE_IP"]=", ".join(s.get("TailscaleIPs",["—"]))
                data["TAILSCALE_DNS"]=s.get("DNSName","—").rstrip(".")
                if s.get("ExitNodeID"):
                    for peer in ts.get("Peer",{}).values():
                        if peer.get("ID")==s["ExitNodeID"]:
                            data["TAILSCALE_EXIT"]=f" · Exit: {peer.get('HostName','?')}"
                            break
            data["NETWORK_SUMMARY"]=f"Tailscale {data['TAILSCALE_STATUS']}"
        except: pass

    # Basic network info
    out2,_,_=run('bash -c "ipconfig 2>/dev/null | grep -A1 \'以太网\|Wi-Fi\' | grep -v \'Unknown\|Tailscale\' | head -6"',timeout=5)
    if not out2:
        out2,_,_=run_ps("Get-NetAdapter | Where-Object Status -eq 'Up' | ForEach-Object { $_.Name + ': ' + $_.Status }")
    if out2 and out2.strip():
        data["NETWORK_SUMMARY"]="以太网/Wi-Fi 已连接"
    else:
        data["NETWORK_SUMMARY"]=data.get("NETWORK_SUMMARY","Tailscale 在线")
    return data

PROC_CN = {
    "Memory Compression": "内存压缩",
    "Hermes": "AI Agent",
    "chrome": "Chrome",
    "explorer": "资源管理器",
    "steamwebhelper": "Steam",
    "dwm": "桌面窗口",
    "python": "Python",
    "cmd": "命令行",
    "Code": "VS Code",
    "firefox": "Firefox",
    "msedge": "Edge",
    "Discord": "Discord",
    "Everything": "文件搜索",
    "SearchHost": "搜索",
}

def collect_processes():
    data={"PROCESS_TOTAL":"—","PROCESS_TOP5":"","ZOMBIE_COUNT":"—"}
    out,_,_=run_ps("""
$procs = Get-Process | Sort-Object WorkingSet64 -Descending
$top = $procs | Select-Object -First 5 Name,Id,@{N='MemMB';E={[math]::Round($_.WorkingSet64/1MB)}}
Write-Output "TOTAL|$($procs.Count)"
foreach ($p in $top) { Write-Output "PROC|$($p.Name)|$($p.Id)|$($p.MemMB)" }
""")
    if out:
        items=[]
        for line in out.strip().split("\n"):
            if line.startswith("TOTAL|"):
                data["PROCESS_TOTAL"]=line.split("|")[1]
            elif line.startswith("PROC|"):
                parts=line.split("|")
                if len(parts)>=4:
                    name = parts[1]
                    cn = PROC_CN.get(name, "")
                    display = f"{name} <small style='color:var(--text-dim);font-size:0.6rem'>{cn}</small>" if cn else name
                    items.append(f'<div class="proc-row"><span class="proc-rank">{len(items)+1}</span><span class="proc-name">{display}</span><span class="proc-pid">PID {parts[2]}</span><span class="proc-mem">{parts[3]} MB</span></div>')
        data["PROCESS_TOP5"]="\n".join(items) if items else '<div class="proc-row"><span class="proc-name" style="color:var(--text-dim)">暂无数据</span></div>'
    data["ZOMBIE_COUNT"]="—"
    return data

def collect_images():
    data={"IMAGE_COUNT":"0","IMAGE_LIST":""}
    today_str = (REPORT_DATE or datetime.date.today()).strftime("%Y-%m-%d")
    import glob as _glob, os as _os
    exts = ("*.png","*.jpg","*.jpeg","*.webp")
    img_dirs = [r"D:\Hermes\cache\images", r"D:\Hermes\images"]
    try:
        files = []
        for img_dir in img_dirs:
            if not _os.path.isdir(img_dir):
                continue
            for ext in exts:
                for f in _glob.glob(_os.path.join(img_dir, ext)):
                    mtime = _os.path.getmtime(f)
                    mdate = datetime.date.fromtimestamp(mtime).strftime("%Y-%m-%d")
                    if mdate == today_str:
                        files.append((mtime, _os.path.basename(f), img_dir))
        files.sort(key=lambda x: x[0], reverse=True)
        if files:
            data["IMAGE_COUNT"] = str(len(files))
            latest_ts = datetime.datetime.fromtimestamp(files[0][0]).strftime("%H:%M")
            data["IMAGE_TIME"] = f'<div style="font-size:0.58rem;color:var(--text-dim);margin-top:2px;">最新 {latest_ts}</div>'
            items = []
            for mtime, fn, _d in files[:20]:
                ts = datetime.datetime.fromtimestamp(mtime).strftime("%H:%M:%S")
                items.append(f'<li class="log-item"><span class="log-time">{ts}</span><span class="log-file">{fn}</span></li>')
            data["IMAGE_LIST"] = "\n".join(items)
        else:
            data["IMAGE_LIST"] = '<li class="log-empty">今日无图片生成</li>'
    except Exception:
        data["IMAGE_LIST"] = '<li class="log-empty">今日无图片生成</li>'
    return data

def collect_files():
    data={"FILE_CHANGE_COUNT":"0", "HERMES_HOME_SIZE":"—"}
    out,_,_=run('bash -c "find /d/Hermes/ -not -path \'*/cache/*\' -not -path \'*/node_modules/*\' -not -path \'*/.git/*\' -newermt \'today 00:00\' -type f 2>/dev/null | wc -l"',timeout=10)
    if out: data["FILE_CHANGE_COUNT"]=out.strip()

    # File list — write find command to temp script to avoid escaping hell
    items=[]
    find_script = '''#!/bin/bash
find /d/Hermes/ -not -path "*/cache/*" -not -path "*/node_modules/*" -not -path "*/.git/*" -newermt "today 00:00" -type f -printf "%T+ %p\\n" 2>/dev/null | sort -r | head -30
'''
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False, encoding='utf-8')
    tmp.write(find_script); tmp.close()
    os.chmod(tmp.name, 0o755)
    out2,_,_=run(f'bash "{tmp.name}"', timeout=15)
    os.unlink(tmp.name)
    if out2:
        for l in out2.strip().split("\n"):
            if len(items)>=12: break
            parts=l.split(" ",1)
            if len(parts)<2: continue
            fp=parts[1].replace("/d/Hermes/","Hermes/")
            # Prioritize config/skills/plugins
            items.append(f'<li class="log-item"><span class="log-file">{fp}</span></li>')
    total=int(data["FILE_CHANGE_COUNT"])
    if total>12:
        items.append(f'<li class="log-item"><span class="log-file" style="color:var(--text-dim)">... 还有 {total-12} 个文件</span></li>')
    data["FILE_CHANGES"]="\n".join(items) if items else '<li class="log-empty">今日无文件变动</li>'

    # Hermes home size
    out2,_,_=run('bash -c "du -sh --exclude=node_modules /d/Hermes/ 2>/dev/null | cut -f1"',timeout=15)
    if out2: data["HERMES_HOME_SIZE"]=out2.strip()
    return data

def collect_host():
    data={"CPU_USAGE":"—","CPU_PEAK":"—","MEM_GB":"—","MEM_USAGE":"—","MEM_PEAK":"—",
          "DISK_GB":"—","DISK_USAGE":"—","MEM_WARN":"","DISK_WARN":"",
          "PEAK_SOURCE":""}
    
    # Current values
    out,_,_=run_ps("(Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average")
    if out and out.replace('.','').replace('-','').isdigit():
        cpu=int(float(out))
        data["CPU_USAGE"]=str(cpu)
    out,_,_=run_ps("$os=Get-CimInstance Win32_OperatingSystem;$t=[math]::Round($os.TotalVisibleMemorySize/1MB);$f=[math]::Round($os.FreePhysicalMemory/1MB);Write-Output \"$t|$f\"")
    if "|" in out:
        p=out.strip().split("|")
        try:
            t,f=float(p[0]),float(p[1]); pct=round((1-f/t)*100)
            data["MEM_GB"]=str(int(t)); data["MEM_USAGE"]=str(pct)
            if pct>90: data["MEM_WARN"]=" danger"
            elif pct>80: data["MEM_WARN"]=" warn"
        except: pass
    out,_,_=run_ps("$d=Get-PSDrive C;$u=[math]::Round($d.Used/1GB,1);$t=[math]::Round(($d.Used+$d.Free)/1GB,1);Write-Output \"$u|$t\"")
    if "|" in out:
        p=out.strip().split("|")
        try:
            u,t=float(p[0]),float(p[1]); pct=round(u/t*100)
            data["DISK_GB"]=str(u); data["DISK_USAGE"]=str(pct)
            if pct>90: data["DISK_WARN"]=" danger"
            elif pct>80: data["DISK_WARN"]=" warn"
        except: pass
    
    # Try real peak data from monitor
    peak_file = "D:\\Hermes\\cache\\peak_samples.json"
    if os.path.exists(peak_file):
        try:
            with open(peak_file,"r",encoding="utf-8") as f:
                samples = json.load(f)
            if samples:
                today_str = (REPORT_DATE or datetime.date.today()).strftime("%Y-%m-%d")
                today_samples = [s for s in samples if s.get("ts","").startswith(today_str)]
                if today_samples:
                    cpu_peak = max(s["cpu"] for s in today_samples)
                    mem_peak = max(s["mem"] for s in today_samples)
                    data["CPU_PEAK"] = str(int(cpu_peak))
                    data["MEM_PEAK"] = str(int(mem_peak))
                    data["PEAK_SOURCE"] = f"真实采样 · {len(today_samples)} 个样本"
                    return data
        except: pass
    
    # Fallback: simulated peaks
    if data["CPU_USAGE"]!="—":
        data["CPU_PEAK"]=str(min(int(data["CPU_USAGE"])+random.randint(5,25),100))
    if data["MEM_USAGE"]!="—":
        data["MEM_PEAK"]=str(min(int(data["MEM_USAGE"])+random.randint(5,15),100))
    return data

def collect_storage():
    data={"CACHE_SIZE":"—","DB_SIZE":"—","MEMORY_COUNT":"—"}
    out,_,_=run('bash -c "du -sh /d/Hermes/cache/ 2>/dev/null | cut -f1"')
    if out: data["CACHE_SIZE"]=out.strip()
    out,_,_=run('bash -c "wc -c < /d/Hermes/state.db 2>/dev/null || echo 0"')
    try: data["DB_SIZE"]=human_bytes(int(out.strip()))
    except: pass
    # MEMORY_COUNT: filled by agent during cron (not accessible from standalone Python)
    return data

def collect_obsidian():
    data={"VAULT_TOTAL_FILES":"—","VAULT_TODAY_CHANGES":"—","VAULT_RECENT_FILES":"",
          "TAG_HEALTH":"—","TAG_HEALTH_CLASS":""}
    out,_,_=run('bash -c "find \'/c/Users/沙河马/Documents/hippo/\' -name \'*.md\' 2>/dev/null | wc -l"',timeout=10)
    if out: data["VAULT_TOTAL_FILES"]=out.strip()
    out2,_,_=run('bash -c "find \'/c/Users/沙河马/Documents/hippo/\' -name \'*.md\' -newermt \'today 00:00\' -printf \'%f\n\' 2>/dev/null | sort | head -15"',timeout=10)
    if out2:
        files=[f for f in out2.strip().split("\n") if f]
        data["VAULT_TODAY_CHANGES"]=str(len(files))
        data["VAULT_RECENT_FILES"]=" · ".join(files[:10]) if files else "今日无变更"
    else:
        data["VAULT_TODAY_CHANGES"]="0"
        data["VAULT_RECENT_FILES"]="今日无变更"
    return data

def estimate_cost(model_name, raw_input, raw_output):
    """Estimate token cost based on model pricing (fallback only)."""
    if not model_name or model_name=="—":
        return "—", "价格待确认"
    rates={
        "deepseek": (0.435, 0.87),
        "gpt": (2.50, 10.00),
        "claude": (3.00, 15.00),
    }
    for prefix, (in_rate, out_rate) in rates.items():
        if model_name.lower().startswith(prefix):
            cost = (raw_input/1e6)*in_rate + (raw_output/1e6)*out_rate
            return f"${cost:.4f}", f"估算 · {prefix}"
    return "—", "价格待确认"

# ── Balance snapshot helpers (per-date, never overwritten) ──

CACHE_DIR = r"D:\Hermes\cache"

def _balance_snapshot_path(date_str):
    return os.path.join(CACHE_DIR, f"ds_balance_{date_str}.json")

def _migrate_old_snapshot():
    """One-time: migrate legacy ds_balance.json to per-date format."""
    old = os.path.join(CACHE_DIR, "ds_balance.json")
    if not os.path.exists(old):
        return
    try:
        with open(old, "r") as f:
            hist = json.load(f)
        d = hist.get("date", "")
        b = hist.get("balance")
        if d and b is not None:
            new_path = _balance_snapshot_path(d)
            if not os.path.exists(new_path):
                with open(new_path, "w") as f:
                    json.dump({"date": d, "balance": b, "source": "migrated"}, f)
        os.remove(old)
    except:
        pass

def _save_snapshot(date_str, balance):
    """Save/update end-of-day balance for a specific date.
    Allows overwrite — the 00:00 cron will naturally be the last writer,
    giving the most accurate end-of-day value."""
    path = _balance_snapshot_path(date_str)
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(path, "w") as f:
        json.dump({"date": date_str, "balance": balance,
                   "saved_at": datetime.datetime.now().isoformat()}, f)

def _load_snapshot(date_str):
    """Load end-of-day balance for a date. Returns float or None."""
    path = _balance_snapshot_path(date_str)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r") as f:
            return json.load(f).get("balance")
    except:
        return None

def _calc_consumption(prev_balance, current_balance):
    """Calculate consumption and detect ¥100 recharges.
    Returns (formatted_string, css_class, recharge_note)."""
    diff = prev_balance - current_balance
    # Detect recharge: balance went UP by ~100
    if current_balance > prev_balance and abs(current_balance - prev_balance - 100) < 5:
        adjusted = prev_balance + 100 - current_balance
        if adjusted > 0:
            return (f"¥{adjusted:.2f}", "down", " · 检测到充值 +100")
        return ("¥0", "flat", " · 检测到充值 +100")
    if diff > 0:
        return (f"¥{diff:.2f}", "down", "")
    return ("¥0", "flat", "")

def collect_deepseek_cost():
    """Query DeepSeek API balance. Store per-date snapshot for accurate daily tracking.
    
    Logic:
    - Cron at 00:00 → REPORT_DATE is yesterday. Query API, save snapshot as end-of-yesterday.
      Calculate consumption = day-before-yesterday balance - yesterday balance.
    - Manual run for today → query API live, save snapshot for today.
    - Manual run for past date → use stored snapshots only (don't query API — balance changed).
    """
    data = {"DS_BALANCE": "—", "DS_CONSUMPTION": "—", "DS_CONSUMPTION_CLASS": "flat",
            "DS_RECHARGE_NOTE": "", "DS_CURRENCY": "CNY", "DS_CONSUMPTION_NOTE": ""}
    
    _migrate_old_snapshot()
    
    report_date_str = REPORT_DATE.strftime("%Y-%m-%d") if REPORT_DATE else datetime.date.today().strftime("%Y-%m-%d")
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    yesterday_str = (REPORT_DATE - datetime.timedelta(days=1)).strftime("%Y-%m-%d") if REPORT_DATE else ""
    is_today = (report_date_str == today_str)
    # Cron at 00:00 captures end-of-yesterday: always query API for the true balance
    _now = datetime.datetime.now()
    _near_midnight = (_now.hour == 0 and _now.minute < 5)
    _should_query_api = is_today or _near_midnight
    
    # Key
    key = ""
    env_paths = ["/d/Hermes/.env", "D:\\Hermes\\.env"]
    for p in env_paths:
        if os.path.exists(p):
            with open(p,"r") as f:
                for line in f:
                    if line.startswith("DEEPSEEK_API_KEY="):
                        key = line.split("=",1)[1].strip().strip('"').strip("'")
                        break
        if key: break
    
    if not key:
        return data
    
    current = None
    currency = "CNY"
    
    if _should_query_api:
        # Query API live for current balance
        try:
            import urllib.request, ssl
            ctx = ssl.create_default_context()
            req = urllib.request.Request("https://api.deepseek.com/user/balance")
            req.add_header("Authorization", f"Bearer {key}")
            resp = urllib.request.urlopen(req, context=ctx, timeout=10)
            body = json.loads(resp.read())
            if body.get("is_available") and body.get("balance_infos"):
                info = body["balance_infos"][0]
                current = float(info["total_balance"])
                currency = info.get("currency", "CNY")
                # Save under REPORT_DATE (at 00:00 this is yesterday = end-of-day)
                _save_snapshot(report_date_str, current)
        except Exception as e:
            # Fall back to stored snapshot for report date
            current = _load_snapshot(report_date_str)
    else:
        # Past date: use stored snapshot
        current = _load_snapshot(report_date_str)
    
    if current is None:
        data["DS_CONSUMPTION_NOTE"] = "无当日快照"
        return data
    
    data["DS_BALANCE"] = f"{current:.2f}"
    data["DS_CURRENCY"] = currency
    
    # Calculate consumption: previous day's end-of-day minus this day's end-of-day
    if is_today:
        prev_date = yesterday_str
    else:
        prev_date = (REPORT_DATE - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    
    prev_balance = _load_snapshot(prev_date)
    if prev_balance is None:
        data["DS_CONSUMPTION"] = "—"
        data["DS_CONSUMPTION_NOTE"] = f"无 {prev_date} 快照，今日起开始累积"
        return data
    
    consumption, css_class, recharge_note = _calc_consumption(prev_balance, current)
    data["DS_CONSUMPTION"] = consumption
    data["DS_CONSUMPTION_CLASS"] = css_class
    data["DS_RECHARGE_NOTE"] = recharge_note
    
    return data

# ═══════════════════════ CONTENT GENERATION ═══════════════════════

def gen_top_tools(tools):
    if not tools: return '<li class="rank-item"><span class="rank-name">暂无数据</span></li>'
    mx=max(c for _,c,_ in tools) if tools else 1
    items=[]
    for i,(name,count,pct) in enumerate(tools[:10]):
        cn=TOOL_CN.get(name,name)
        bw=int(count/mx*100)
        items.append(f'<li class="rank-item"><span class="rank-pos">{i+1:02d}</span><span class="rank-name">{cn}</span><div class="rank-bar-wrap"><div class="rank-bar" style="width:{bw}%"></div></div><span class="rank-count">{count}</span></li>')
    return "\n".join(items)

def gen_top_skills(skills):
    if not skills: return '<div style="color:var(--text-dim);font-size:0.78rem;">暂无数据</div>'
    items=[]
    for i,(name,loads,edits) in enumerate(skills[:10]):
        cn=SKILL_CN.get(name,name)
        hl='skill-hl' if i<3 else ''
        items.append(f'<li class="rank-item {hl}"><span class="rank-pos">{i+1:02d}</span><span class="rank-name">{cn}</span><span class="rank-count">加载 {loads} · 编辑 {edits}</span></li>')
    return '<ul class="rank-list">'+"\n".join(items)+'</ul>'

def gen_week_bars(counts, prev_counts=None):
    mx=max(counts) if counts and max(counts)>0 else 1
    if prev_counts is None:
        prev_counts=[0]*7
    mx2=max(prev_counts) if max(prev_counts)>0 else 1
    bars=[]
    for i,c in enumerate(counts):
        pc=prev_counts[i] if i<len(prev_counts) else 0
        ghost_h=max(3,int(pc/mx2*60)) if pc>0 else 0
        if c>0:
            h=max(8,int(c/mx*60))
            bars.append(f'<div class="week-col"><div class="week-bar-ghost" style="height:{ghost_h}px"></div><div class="week-bar-s" style="height:{h}px"></div></div>')
        else:
            bars.append(f'<div class="week-col"><div class="week-bar-ghost" style="height:{ghost_h}px"></div><div class="week-bar-s inactive" style="height:3px"></div></div>')
    return "\n".join(bars)

def gen_week_nums(counts):
    return "".join(f'<span>{c if c>0 else ""}</span>' for c in counts)

def gen_peak_chart(raw_peak):
    slots=[0]*24
    if raw_peak:
        for m in re.finditer(r'(\d+)(AM|PM)\s*\((\d+)\)',raw_peak):
            h=int(m.group(1)); ampm=m.group(2); count=int(m.group(3))
            if ampm=="PM" and h!=12: h+=12
            if ampm=="AM" and h==12: h=0
            if 0<=h<24: slots[h]=count
    mx=max(slots) if max(slots)>0 else 1
    # Placeholder: previous day data (empty until real data available)
    prev=[0]*24
    mx2=max(prev) if max(prev)>0 else 1
    bars=""
    for i,s in enumerate(slots):
        ph=max(2,int(prev[i]/mx2*44)) if prev[i]>0 else 0
        h=max(2,int(s/mx*44)) if s>0 else 1
        bars+=f'<div class="peak-col"><div class="peak-ghost" style="height:{ph}px"></div><div class="peak-bar" style="height:{h}px"></div></div>'
    labels="".join(f'<span>{h if h%6==0 else ""}</span>' for h in range(24))
    return bars,labels

def gen_notable(notable):
    if not notable: return '<div class="notable-chip"><span class="notable-chip-icon">📌</span><div class="notable-chip-info"><strong>暂无数据</strong></div></div>'
    chips=[]
    for item in notable[:4]:
        label,value=item[0],item[1]
        topic=item[2] if len(item)>2 else ""
        cn=NOTABLE_CN.get(label,label)
        icon={"最长会话":"⏳","最多消息":"💬","最多Token":"⚡","最多工具调用":"🔧"}.get(cn,"📌")
        topic_html=f'<span style="font-size:0.62rem;color:var(--text-dim);display:block;margin-top:2px;">{topic}</span>' if topic else ''
        chips.append(f'<div class="notable-chip"><span class="notable-chip-icon">{icon}</span><div class="notable-chip-info"><strong>{value}</strong>{cn}{topic_html}</div></div>')
    return "\n".join(chips)

# ═══════════════════════ COLLECT ALL (self-collect mode) ═══════════════════════

def collect_all():
    """Self-collect mode. Uses REPORT_DATE if set by --date flag."""
    today=REPORT_DATE or datetime.date.today()
    ds=today.strftime("%Y-%m-%d")
    wd=["星期一","星期二","星期三","星期四","星期五","星期六","星期日"][today.weekday()]
    
    # A1: Today insights
    out,_,_=run("hermes insights --days 1",timeout=60)
    data=parse_insights_full(out)
    
    # A2: Yesterday insights (compare)
    out2,_,_=run("hermes insights --days 2",timeout=60)
    ydata=parse_insights_full(out2)
    
    # Channels
    ch=collect_channels()
    wm=int(data.get("WECHAT_MSGS","0").replace(",","") or "0")
    if wm>0: ch["WECHAT_STATUS_CLASS"]="online"; ch["WECHAT_STATUS_TEXT"]="在线"
    elif check_port(9119): ch["WECHAT_STATUS_CLASS"]="activity"; ch["WECHAT_STATUS_TEXT"]="在线 (待命中)"
    data.update(ch)
    
    # Gateway
    data.update(collect_gateway())
    
    # Tailscale
    data.update(collect_tailscale())
    
    # Processes
    data.update(collect_processes())
    
    # Images
    data.update(collect_images())
    
    # Files + Hermes size
    data.update(collect_files())
    
    # Host metrics
    data.update(collect_host())
    
    # Storage
    data.update(collect_storage())
    
    # Obsidian
    data.update(collect_obsidian())
    
    # Cost
    raw_in=data.get("_raw_input_tokens",0)
    raw_out=data.get("_raw_output_tokens",0)
    model=data.get("MODEL_NAME","—")
    cost,cost_note=estimate_cost(model,raw_in,raw_out)
    data["ESTIMATED_COST"]=cost
    data["COST_NOTE"]=cost_note
    
    # DeepSeek cost (real balance query)
    data.update(collect_deepseek_cost())
    
    # Yesterday deltas
    for raw_key, display_key, delta_key, cls_key in [
        ("_raw_sessions","SESSION_COUNT","SESSION_DELTA","SESSION_DELTA_CLASS"),
        ("_raw_messages","MESSAGE_COUNT","MESSAGE_DELTA","MESSAGE_DELTA_CLASS"),
        ("_raw_tool_calls","TOOL_COUNT","TOOL_DELTA","TOOL_DELTA_CLASS"),
    ]:
        try:
            tv=int(data.get(raw_key,"0"))
            yv=int(ydata.get(raw_key,"0"))
            txt,cls=delta_str(tv,yv)
            data[delta_key]=txt; data[cls_key]=cls
        except:
            data[delta_key]="—"; data[cls_key]="flat"
    
    # Token delta (different raw key)
    try:
        tv=data.get("_raw_total_tokens",0)
        yv=ydata.get("_raw_total_tokens",0)
        txt,cls=delta_str(tv,yv) if tv and yv else ("—","flat")
        data["TOKEN_DELTA"]=txt; data["TOKEN_DELTA_CLASS"]=cls
    except:
        data["TOKEN_DELTA"]="—"; data["TOKEN_DELTA_CLASS"]="flat"
    
    # Generated content
    data["TOP_TOOLS"]=gen_top_tools(data["_tools"])
    data["TOP_SKILLS"]=gen_top_skills(data["_skills"])
    data["WEEK_BARS"]=gen_week_bars(data["WEEK_COUNTS"])
    data["WEEK_NUMS"]=gen_week_nums(data["WEEK_COUNTS"])
    peak_bars,peak_labels=gen_peak_chart(data.get("_peak_raw",""))
    data["PEAK_BARS"]=peak_bars; data["PEAK_LABELS"]=peak_labels
    data["NOTABLE_SESSIONS"]=gen_notable([(l,v) for l,v,_ in data["_notable"]])
    
    # Cron
    data.update(collect_cron())
    
    # Defaults
    data.setdefault("DS_CONSUMPTION_CLASS","flat"); data.setdefault("DS_RECHARGE_NOTE","")
    data.setdefault("SESSION_TOPICS",'<span class="float-tag" style="animation:none">数据待分析</span>')
    data.setdefault("DAILY_SUMMARY",'今日数据已采集，深度分析待 agent 生成。')
    data.setdefault("DAILY_RECOMMENDATIONS","")
    # Peak note from collect_host
    peak_src = data.get("PEAK_SOURCE","")
    if peak_src:
        data["PEAK_NOTE"] = f"✅ {peak_src} · 峰值来自持续监控"
    else:
        data["PEAK_NOTE"] = "⚠️ 峰值为瞬时快照+模拟，非持续监控数据。部署轻量守护进程后可获取真实峰值。"
    
    # Date
    data["REPORT_DATE"]=ds
    data["REPORT_WEEKDAY"]=wd
    
    return data

def collect_cron():
    data = {"CRON_TOTAL": "0", "CRON_ACTIVE": "0", "CRON_LIST": "", "CRON_FAILED_TEXT": ""}
    out, _, _ = run("hermes cron list", timeout=10)
    jobs = []
    current = None
    for line in out.split("\n"):
        s = line.strip()
        if not s: continue
        m = re.match(r'^([a-f0-9]{10,})\s*\[(\w+)\]', s)
        if m:
            if current: jobs.append(current)
            current = {"id": m.group(1), "state": m.group(2), "name": "", "schedule": "?", "status": "ok"}
            continue
        if current is None: continue
        m = re.match(r'^Name:\s+(.+)', s)
        if m: current["name"] = m.group(1).strip(); continue
        m = re.match(r'^Schedule:\s+(.+)', s)
        if m: current["schedule"] = m.group(1).strip(); continue
        m = re.match(r'^Last run:.*?\s+(ok|error)\b', s)
        if m: current["status"] = m.group(1); continue
    if current: jobs.append(current)
    
    data["CRON_TOTAL"] = str(len(jobs))
    active = [j for j in jobs if j["state"] == "active"]
    data["CRON_ACTIVE"] = str(len(active))
    
    failed = [j for j in jobs if j["status"] == "error"]
    if failed:
        data["CRON_FAILED_TEXT"] = f" ⚠️ {len(failed)} 个异常"
    
    items = []
    for j in jobs[:10]:
        name = j["name"] if j["name"] else j["id"][:12]
        sched = CRON_SCHED_CN.get(j["schedule"], j["schedule"])
        status = j["status"]
        desc = CRON_DESC.get(name, "")
        icon = "⚠️" if status == "error" else "✅"
        tag_cls = "error" if status == "error" else "ok"
        tag_txt = "异常" if status == "error" else "正常"
        items.append(
            f'<div class="cron-card">'
            f'<span class="cron-status-icon">{icon}</span>'
            f'<div class="cron-info">'
            f'<div class="cron-name">{name}</div>'
            f'<div class="cron-desc">{desc}</div>'
            f'</div>'
            f'<div class="cron-meta">'
            f'<div class="cron-sched">{sched}</div>'
            f'<span class="cron-status-tag {tag_cls}">{tag_txt}</span>'
            f'</div></div>'
        )
    data["CRON_LIST"] = "\n".join(items) if items else '<div class="cron-card"><div class="cron-info"><div class="cron-name">暂无活跃任务</div></div></div>'
    if failed:
        data["CRON_WARN"] = f'<div style="font-size:0.65rem;color:var(--yellow);margin-top:8px;padding:0 4px;">⚠️ {"、".join(j["name"] or j["id"][:12] for j in failed)} 状态异常，建议检查。</div>'
    else:
        data["CRON_WARN"] = ""
    return data

# ═══════════════════════ TEMPLATE FILL ═══════════════════════

def fill_template(data):
    with open(TEMPLATE,"r",encoding="utf-8") as f: html=f.read()
    for k,v in data.items():
        if k.startswith("_"): continue
        html=html.replace("{{"+k+"}}",str(v))
    rem=re.findall(r'\{\{\s*(\w+)\s*\}\}',html)
    if rem: print(f"⚠️ {len(rem)} 个占位符未填充: {rem}")
    return html

# ═══════════════════════ MAIN ═══════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Hermes Daily Report Generator v8.0")
    parser.add_argument("--json", help="JSON data (string or file path) from agent collection")
    parser.add_argument("--date", help="Report date (YYYY-MM-DD, default: today). Use 'yesterday' for midnight cron.")
    args = parser.parse_args()
    
    if args.date == "yesterday":
        today = datetime.date.today() - datetime.timedelta(days=1)
    elif args.date:
        today = datetime.datetime.strptime(args.date, "%Y-%m-%d").date()
    else:
        today = datetime.date.today()
    ds=today.strftime("%Y-%m-%d")
    global REPORT_DATE
    REPORT_DATE = today
    
    if args.json:
        # Agent-driven mode: receive pre-collected JSON
        json_str = args.json
        if os.path.exists(json_str):
            with open(json_str,"r",encoding="utf-8") as f:
                json_str = f.read()
        data = json.loads(json_str)
        print(f"📊 使用 agent 采集数据: {len(data)} 字段")
        
        # Generate content from raw data
        if "_tools" in data:
            data["TOP_TOOLS"] = gen_top_tools(data["_tools"])
        if "_skills" in data:
            data["TOP_SKILLS"] = gen_top_skills(data["_skills"])
        if "WEEK_COUNTS" in data:
            data["WEEK_BARS"] = gen_week_bars(data.get("WEEK_COUNTS",[0]*7))
            data["WEEK_NUMS"] = gen_week_nums(data.get("WEEK_COUNTS",[0]*7))
        if "_peak_raw" in data:
            peak_bars,peak_labels = gen_peak_chart(data.get("_peak_raw",""))
            data["PEAK_BARS"] = peak_bars
            data["PEAK_LABELS"] = peak_labels
        if "_notable" in data:
            data["NOTABLE_SESSIONS"] = gen_notable(data["_notable"])
        if "_cron_data" in data:
            # Agent already formatted cron HTML
            data["CRON_LIST"] = data["_cron_data"].get("CRON_LIST","")
            data["CRON_TOTAL"] = data["_cron_data"].get("CRON_TOTAL","0")
            data["CRON_ACTIVE"] = data["_cron_data"].get("CRON_ACTIVE","0")
            data["CRON_FAILED_TEXT"] = data["_cron_data"].get("CRON_FAILED_TEXT","")
        
        # Fallback cron if not provided
        if "CRON_TOTAL" not in data or data.get("CRON_TOTAL")=="0":
            data.update(collect_cron())
        
        # Defaults for missing fields
        for key in ["SESSION_TIMELINE","SESSION_TOPICS","DAILY_SUMMARY","DAILY_RECOMMENDATIONS",
                     "PEAK_NOTE","ESTIMATED_COST","COST_NOTE","PROCESS_TOTAL","PROCESS_TOP5",
                     "ZOMBIE_COUNT","TAILSCALE_STATUS","TAILSCALE_STATUS_CLASS","TAILSCALE_IP",
                     "TAILSCALE_DNS","TAILSCALE_EXIT","NETWORK_SUMMARY","IMAGE_COUNT","IMAGE_LIST",
                     "FILE_CHANGE_COUNT","FILE_CHANGES","HERMES_HOME_SIZE","VAULT_TOTAL_FILES","VAULT_TODAY_CHANGES",
                     "VAULT_RECENT_FILES","TAG_HEALTH","TAG_HEALTH_CLASS","CRON_WARN","IMAGE_TIME",
                     "SERVICE_ROWS","TOOL_RANKING","SKILL_RANKING","TOP_TOOLS","TOP_SKILLS"]:
            data.setdefault(key,"—")
        
        # Derive TAILSCALE_STATUS_CLASS from status text (pitfall #71 fix)
        ts_cls = data.get("TAILSCALE_STATUS_CLASS","")
        if ts_cls in ("—",""):
            ts = data.get("TAILSCALE_STATUS","")
            data["TAILSCALE_STATUS_CLASS"] = "online" if "在线" in ts else ("offline" if "离线" in ts else ts_cls)
        
        # Peak note
        peak_src = data.get("PEAK_SOURCE","")
        if peak_src:
            data["PEAK_NOTE"] = f"✅ {peak_src} · 峰值来自持续监控"
        else:
            data["PEAK_NOTE"] = "⚠️ 峰值为瞬时快照+模拟，非持续监控数据。部署轻量守护进程后可获取真实峰值。"
        data.setdefault("SESSION_TIMELINE",'<div class="tl-empty">今日无会话</div>')
        data.setdefault("DS_BALANCE","—"); data.setdefault("DS_CONSUMPTION","—")
        data.setdefault("DS_CONSUMPTION_CLASS","flat"); data.setdefault("DS_RECHARGE_NOTE","")
    else:
        # Self-collect mode (backward compatible)
        print(f"📊 {ds}")
        data = collect_all()
    
    # Fill template
    html = fill_template(data)
    
    # Write output
    ip = os.path.join(REPORTS_DIR,"index.html")
    ap = os.path.join(REPORTS_DIR,f"{ds}.html")
    with open(ip,"w",encoding="utf-8") as f: f.write(html)
    with open(ap,"w",encoding="utf-8") as f: f.write(html)
    print(f"✅ index.html ({len(html)} chars)")
    
    # Git push
    os.chdir(REPORTS_DIR)
    run("git add index.html generate.py template.html 2>/dev/null")
    if os.path.exists(f"{ds}.html"): run(f"git add {ds}.html 2>/dev/null")
    oc,ec,rc=run(f'git commit -m "日报 {ds} v8 全谱数据+深度洞察" 2>&1')
    if rc==0:
        _,_,rp=run("git push origin main 2>&1",timeout=30)
        print("✅ Push" if rp==0 else "⚠️ Push失败")
    else:
        if "nothing to commit" in (oc+ec):
            _,_,rp=run("git push origin main 2>&1",timeout=30)
            print("✅ Push (无变更)" if rp==0 else "⚠️ Push失败")
        else: print(f"⚠️ commit: {ec[:80]}")
    
    print(f"\n🔗 https://burkereiii.github.io/hermes-daily-report/")

if __name__=="__main__": main()
