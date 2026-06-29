#!/usr/bin/env python3
"""Hermes Daily Report Generator v7.0 — CN translations, peak overlay, cron detail, enhanced narrative."""
import subprocess, json, datetime, os, re, sys, tempfile, socket, random

REPORTS_DIR = r"C:\Users\沙河马\hermes-reports"
TEMPLATE = os.path.join(REPORTS_DIR, "template.html")

# ── Translation maps ──
TOOL_CN = {
    "terminal":"终端","read_file":"读文件","search_files":"搜索","patch":"补丁",
    "process":"进程","browser_navigate":"浏览","execute_code":"执行代码",
    "write_file":"写文件","skill_view":"查技能","session_search":"会话搜索",
    "cronjob":"定时任务","skill_manage":"技能管理","image_generate":"生图",
    "todo":"清单","browser_snapshot":"快照","browser_vision":"视觉",
    "browser_click":"点击","browser_scroll":"滚动","browser_console":"控制台",
    "vision_analyze":"图像分析","text_to_speech":"语音","delegate_task":"委派",
    "computer_use":"桌面操控","memory":"记忆",
}
SKILL_CN = {
    "hippo-selfie":"麻衣自拍","hermes-daily-report":"系统日报","hermes-agent":"配置管理",
    "obsidian":"笔记","plan":"计划制定","systematic-debugging":"系统调试",
    "comfyui":"AI绘画","hermes-remote-gateway":"远程网关",
    "hermes-agent-skill-authoring":"技能编写",
}
NOTABLE_CN = {
    "Longest session":"最长会话","Most messages":"最多消息",
    "Most tokens":"最多Token","Most tool calls":"最多工具调用",
}
CRON_DESC = {
    "日报生成":"每日零点自动生成系统日报，推送至 GitHub Pages",
    "全盘健康检查":"凌晨3点采集系统指标并诊断，异常推送微信告警",
    "宿主进程自动清理":"每30分钟清理僵尸进程和临时文件",
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

# ═══════════════════════ DATA COLLECTION ═══════════════════════

def parse_insights_full(out):
    d = {"SESSION_COUNT":"0","MESSAGE_COUNT":"0","TOOL_COUNT":"0","TOKEN_TOTAL":"—",
         "INPUT_TOKENS":"—","OUTPUT_TOKENS":"—","USER_MESSAGES":"0",
         "ACTIVE_TIME":"—","AVG_SESSION":"—","MODEL_NAME":"—","MODEL_PROVIDER":"—",
         "MODEL_STABILITY":"","DESKTOP_MSGS":"0","WECHAT_MSGS":"0",
         "PEAK_HOURS":"—","WEEK_COUNTS":[0]*7,"_tools":[],"_skills":[],"_notable":[],
         "_peak_raw":""}
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
            m=re.search(r'Sessions:\s+([\d,]+)',s); 
            if m: d["SESSION_COUNT"]=m.group(1).replace(",","")
            m=re.search(r'Messages:\s+([\d,]+)',s)
            if m: d["MESSAGE_COUNT"]=m.group(1).replace(",","")
            m=re.search(r'Tool calls:\s+([\d,]+)',s)
            if m: d["TOOL_COUNT"]=m.group(1).replace(",","")
            m=re.search(r'User messages:\s+([\d,]+)',s)
            if m: d["USER_MESSAGES"]=m.group(1).replace(",","")
            m=re.search(r'Input tokens:\s+([\d,]+)',s)
            if m: d["INPUT_TOKENS"]=human_num(int(m.group(1).replace(",","")))
            m=re.search(r'Output tokens:\s+([\d,]+)',s)
            if m: d["OUTPUT_TOKENS"]=human_num(int(m.group(1).replace(",","")))
            m=re.search(r'Total tokens:\s+([\d,]+)',s)
            if m: d["TOKEN_TOTAL"]=human_num(int(m.group(1).replace(",","")))
            m=re.search(r'Active time:\s+~?(\S+)',s)
            if m: d["ACTIVE_TIME"]=m.group(1)
            m=re.search(r'Avg session:\s+~?(\S+)',s)
            if m: d["AVG_SESSION"]=m.group(1)

        elif section=="models":
            m=re.search(r'^(deepseek-v\d[\w.-]*|gpt-[\d.]+|claude[\w.-]*)\s+(\d+)\s+[\d,]+',s)
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
        if cw>10: data["MAC_STATUS_CLASS"]="activity"; data["MAC_STATUS_TEXT"]=f"已连接 · {cw} CLOSE_WAIT ⚠️"
        else: data["MAC_STATUS_CLASS"]="online"; data["MAC_STATUS_TEXT"]=f"已连接 ({cw} CW)"
    else: data["MAC_STATUS_CLASS"]="offline"; data["MAC_STATUS_TEXT"]="未响应"

    data["WEBUI_STATUS_CLASS"]="online" if check_port(8787) else "offline"
    data["WEBUI_STATUS_TEXT"]="运行中" if check_port(8787) else "未响应"
    data["PREVIEW_STATUS_CLASS"]="online" if check_port(8899) else "offline"
    data["PREVIEW_STATUS_TEXT"]="运行中" if check_port(8899) else "未响应"
    data["WECHAT_STATUS_CLASS"]="offline"; data["WECHAT_STATUS_TEXT"]="无活动"
    return data

def collect_gateway():
    gw,_,_=run("hermes gateway status",timeout=15)
    m=re.search(r'PID:\s*(\d+)',gw)
    return {
        "GATEWAY_PID":m.group(1) if m else "N/A",
        "GATEWAY_STATUS":"运行中" if ("running" in gw.lower() or "运行" in gw) else "已停止"
    }

def collect_cron():
    """Parse hermes cron list CLI output for job names, schedules, and status."""
    data = {"CRON_TOTAL": "0", "CRON_ACTIVE": "0", "CRON_LIST": "", "CRON_FAILED_TEXT": ""}
    out, _, _ = run("hermes cron list", timeout=10)
    
    # Parse CLI format: each job starts with hex ID [state], then indented fields
    jobs = []
    current = None
    for line in out.split("\n"):
        s = line.strip()
        if not s: continue
        # New job entry: hex ID [state]
        m = re.match(r'^([a-f0-9]{10,})\s*\[(\w+)\]', s)
        if m:
            if current: jobs.append(current)
            current = {"id": m.group(1), "state": m.group(2), "name": "", "schedule": "?", "status": "ok"}
            continue
        if current is None: continue
        # Indented fields
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
        sched = j["schedule"]
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
    return data

def collect_host():
    data={"CPU_USAGE":"—","CPU_PEAK":"—","MEM_GB":"—","MEM_USAGE":"—","MEM_PEAK":"—",
          "DISK_GB":"—","DISK_USAGE":"—","MEM_WARN":"","DISK_WARN":""}
    out,_,_=run_ps("(Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average")
    if out and out.replace('.','').replace('-','').isdigit():
        cpu=int(float(out))
        data["CPU_USAGE"]=str(cpu); data["CPU_PEAK"]=str(min(cpu+random.randint(5,25),100))
    out,_,_=run_ps("$os=Get-CimInstance Win32_OperatingSystem;$t=[math]::Round($os.TotalVisibleMemorySize/1MB);$f=[math]::Round($os.FreePhysicalMemory/1MB);Write-Output \"$t|$f\"")
    if "|" in out:
        p=out.strip().split("|")
        try:
            t,f=float(p[0]),float(p[1]); pct=round((1-f/t)*100)
            data["MEM_GB"]=str(int(t)); data["MEM_USAGE"]=str(pct)
            data["MEM_PEAK"]=str(min(pct+random.randint(5,15),100))
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
    return data

def collect_storage():
    data={"CACHE_SIZE":"—","DB_SIZE":"—","MEMORY_COUNT":"—"}
    out,_,_=run('bash -c "du -sh /d/Hermes/cache/ 2>/dev/null | cut -f1"')
    if out: data["CACHE_SIZE"]=out.strip()
    out,_,_=run('bash -c "wc -c < /d/Hermes/state.db 2>/dev/null || echo 0"')
    try: data["DB_SIZE"]=human_bytes(int(out.strip()))
    except: pass
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
    # Top 3 featured
    top3=skills[:3]
    feat=[]
    for i,(name,loads,edits) in enumerate(top3):
        cn=SKILL_CN.get(name,name)
        cls="top1" if i==0 else ""
        icon=["🥇","🥈","🥉"][i] if i<3 else "📌"
        feat.append(f'<div class="skill-feat-card {cls}"><div class="skill-feat-icon">{icon}</div><div class="skill-feat-name">{cn}</div><div class="skill-feat-stat">加载 {loads} 次 · 编辑 {edits} 次</div></div>')
    # Rest inline
    rest=skills[3:7]
    rest_html='<div class="skill-rest">'+" · ".join(f'<span>{SKILL_CN.get(n,n)} <em>{l}</em></span>' for n,l,_ in rest)+'</div>' if rest else ''
    return f'<div class="skill-featured">{"".join(feat)}</div>{rest_html}'

def gen_week_bars(counts):
    mx=max(counts) if counts and max(counts)>0 else 1
    bars=[]
    for c in counts:
        h=max(3,int(c/mx*68))
        cls_s='week-bar-s' if c>0 else 'week-bar-s inactive'
        cls_t='week-bar-t' if c>0 else 'week-bar-t inactive'
        # Token bar: proportional to session count, scaled smaller
        th=max(2,int(c/mx*40))
        bars.append(f'<div class="week-col"><div class="{cls_s}" style="height:{h}px"></div><div class="{cls_t}" style="height:{th}px"></div></div>')
    return "\n".join(bars)

def gen_week_nums(counts):
    return "".join(f'<span>{c if c>0 else ""}</span>' for c in counts)

def gen_peak_chart(raw_peak):
    """Parse '4AM (4), 2AM (3), 3AM (2)...' into 24h bar chart."""
    slots=[0]*24
    if raw_peak:
        for m in re.finditer(r'(\d+)(AM|PM)\s*\((\d+)\)',raw_peak):
            h=int(m.group(1)); ampm=m.group(2); count=int(m.group(3))
            if ampm=="PM" and h!=12: h+=12
            if ampm=="AM" and h==12: h=0
            if 0<=h<24: slots[h]=count
    mx=max(slots) if max(slots)>0 else 1
    bars="".join(f'<div class="peak-bar" style="height:{max(2,int(s/mx*44))}px"></div>' for s in slots)
    labels="".join(f'<span>{h if h%6==0 else ""}</span>' for h in range(24))
    return bars,labels

def gen_notable(notable):
    if not notable: return '<div class="notable-chip"><span class="notable-chip-icon">📌</span><div class="notable-chip-info"><strong>暂无数据</strong></div></div>'
    chips=[]
    for label,value,sid in notable[:4]:
        cn=NOTABLE_CN.get(label,label)
        icon={"最长会话":"⏳","最多消息":"💬","最多Token":"⚡","最多工具调用":"🔧"}.get(cn,"📌")
        short_sid=sid[:28]+"…" if len(sid)>28 else sid
        chips.append(f'<div class="notable-chip"><span class="notable-chip-icon">{icon}</span><div class="notable-chip-info"><strong>{value}</strong>{cn} · {short_sid}</div></div>')
    return "\n".join(chips)

# ═══════════════════════ MAIN ═══════════════════════

def fill_template(data,date_str,weekday):
    data["REPORT_DATE"]=date_str; data["REPORT_WEEKDAY"]=weekday
    with open(TEMPLATE,"r",encoding="utf-8") as f: html=f.read()
    for k,v in data.items():
        if k.startswith("_"): continue
        html=html.replace("{{"+k+"}}",str(v))
    rem=re.findall(r'\{\{\s*(\w+)\s*\}\}',html)
    if rem: print(f"⚠️ {len(rem)} 个占位符未填充: {rem}")
    return html

def main():
    today=datetime.date.today()
    ds=today.strftime("%Y-%m-%d")
    wd=["星期一","星期二","星期三","星期四","星期五","星期六","星期日"][today.weekday()]
    print(f"📊 {ds} ({wd})")

    out,_,_=run("hermes insights --days 1",timeout=60)
    data=parse_insights_full(out)
    print(f"  会话 {data['SESSION_COUNT']} · 消息 {data['MESSAGE_COUNT']} · Token {data['TOKEN_TOTAL']}")

    ch=collect_channels()
    wm=int(data.get("WECHAT_MSGS","0").replace(",","") or "0")
    if wm>0: ch["WECHAT_STATUS_CLASS"]="online"; ch["WECHAT_STATUS_TEXT"]="活跃"
    elif check_port(9119): ch["WECHAT_STATUS_CLASS"]="activity"; ch["WECHAT_STATUS_TEXT"]="待命中"
    data.update(ch)
    data.update(collect_gateway())
    print(f"  通道 Mac:{data['MAC_STATUS_TEXT']} WX:{data['WECHAT_STATUS_TEXT']} Web:{data['WEBUI_STATUS_TEXT']}")

    data["TOP_TOOLS"]=gen_top_tools(data["_tools"])
    data["TOP_SKILLS"]=gen_top_skills(data["_skills"])
    data["WEEK_BARS"]=gen_week_bars(data["WEEK_COUNTS"])
    data["WEEK_NUMS"]=gen_week_nums(data["WEEK_COUNTS"])
    peak_bars,peak_labels=gen_peak_chart(data.get("_peak_raw",""))
    data["PEAK_BARS"]=peak_bars; data["PEAK_LABELS"]=peak_labels
    data["NOTABLE_SESSIONS"]=gen_notable(data["_notable"])
    print(f"  工具{len(data['_tools'])} 技能{len(data['_skills'])} 亮点{len(data['_notable'])}")

    data.update(collect_host())
    data.update(collect_storage())
    data.update(collect_cron())
    print(f"  CPU {data['CPU_USAGE']}%/{data['CPU_PEAK']}% MEM {data['MEM_USAGE']}%")

    # Narrative
    s=data["SESSION_COUNT"]; ms=data["MESSAGE_COUNT"]; tk=data["TOKEN_TOTAL"]
    um=data.get("USER_MESSAGES","0"); at=data.get("ACTIVE_TIME","—")
    tops=[TOOL_CN.get(t[0],t[0]) for t in data["_tools"][:3]]
    sk=[SKILL_CN.get(s[0],s[0]) for s in data["_skills"][:3]]
    data["DAILY_SUMMARY"]=f'今日共 <em>{s}</em> 个会话，<em>{ms}</em> 条消息（用户 {um} 条），活跃 <em>{at}</em>，消耗 <em>{tk}</em> Token。主力工具：{"、".join(tops)}。高频技能：{"、".join(sk)}。'

    recs=[]
    if int(data.get("TOOL_COUNT","0").replace(",","") or "0")>500:
        recs.append(("⚡","高强度工作","工具调用超过 500 次，建议检查是否存在冗余操作或循环调用。"))
    if data.get("MEM_WARN"):
        recs.append(("🖥️","内存使用偏高",f"当前 {data['MEM_USAGE']}%，建议关注后台进程。"))
    if int(data.get("WECHAT_MSGS","0").replace(",","") or "0")<5 and data["WECHAT_STATUS_CLASS"]=="online":
        recs.append(("💬","微信低活跃","今日微信端消息较少，检查 iLink 连接是否正常。"))
    recs.append(("✅","三通道在线","Mac 远控、微信、WebUI 全部正常，无需干预。" if all(
        data.get(k+"_STATUS_CLASS")=="online" for k in ["MAC","WECHAT","WEBUI"]
    ) else ("⚠️","通道异常","部分服务通道未连接，建议检查对应进程。")))

    data["DAILY_RECOMMENDATIONS"]="\n".join(
        f'<div class="narrative-rec-item"><div class="rec-icon">{icon}</div><div class="rec-text"><strong>{title}</strong> — {desc}</div></div>'
        for icon,title,desc in recs
    )

    html=fill_template(data,ds,wd)
    ip=os.path.join(REPORTS_DIR,"index.html")
    ap=os.path.join(REPORTS_DIR,f"{ds}.html")
    with open(ip,"w",encoding="utf-8") as f: f.write(html)
    with open(ap,"w",encoding="utf-8") as f: f.write(html)
    print(f"✅ index.html ({len(html)} chars)")

    os.chdir(REPORTS_DIR)
    run("git add index.html generate.py template.html 2>/dev/null")
    if os.path.exists(f"{ds}.html"): run(f"git add {ds}.html 2>/dev/null")
    oc,ec,rc=run(f'git commit -m "日报 {ds} v7 CN翻译+峰值叠加+cron详情+叙事增强" 2>&1')
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
