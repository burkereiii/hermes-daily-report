import json

data = {
    "REPORT_DATE": "2026-06-30",
    "REPORT_WEEKDAY": "星期二",
    
    "SESSION_COUNT": "8", "SESSION_DELTA": "↑ 1 (14%)", "SESSION_DELTA_CLASS": "up",
    "MESSAGE_COUNT": "1,577", "MESSAGE_DELTA": "↓ 457 (22%)", "MESSAGE_DELTA_CLASS": "down",
    "TOKEN_TOTAL": "95.5M", "TOKEN_DELTA": "↓ 86.2M (47%)", "TOKEN_DELTA_CLASS": "down",
    "TOOL_COUNT": "776", "TOOL_DELTA": "↑ 14 (2%)", "TOOL_DELTA_CLASS": "up",
    "USER_MESSAGES": "86", "ACTIVE_TIME": "19h 50m", "AVG_SESSION": "3h 58m",
    "INPUT_TOKENS": "921.1K", "OUTPUT_TOKENS": "338.0K",
    
    "MODEL_NAME": "deepseek-v4-pro", "MODEL_PROVIDER": "DeepSeek", "MODEL_STABILITY": " · 单模型 · 无 fallback",
    "DESKTOP_MSGS": "1,071", "WECHAT_MSGS": "435",
    "GATEWAY_PID": "31852", "GATEWAY_STATUS": "运行中",
    
    "MAC_STATUS_CLASS": "online", "MAC_STATUS_TEXT": "已连接 (0 CW)",
    "WEBUI_STATUS_CLASS": "online", "WEBUI_STATUS_TEXT": "运行中",
    "PREVIEW_STATUS_CLASS": "online", "PREVIEW_STATUS_TEXT": "运行中",
    "WECHAT_STATUS_CLASS": "online", "WECHAT_STATUS_TEXT": "活跃",
    
    "TAILSCALE_STATUS": "在线", "TAILSCALE_STATUS_CLASS": "online",
    "TAILSCALE_IP": "100.64.111.119", "TAILSCALE_DNS": "node.tailbfef97.ts.net",
    "TAILSCALE_EXIT": "", "NETWORK_SUMMARY": "Tailscale 在线 · 以太网已连接 · 三通道端口全部 LISTENING",
    
    "PROCESS_TOTAL": "384",
    "PROCESS_TOP5": '<div class="proc-row"><span class="proc-rank">1</span><span class="proc-name">Memory Compression</span><span class="proc-pid">4656</span><span class="proc-mem">933 MB</span></div>\n<div class="proc-row"><span class="proc-rank">2</span><span class="proc-name">chrome</span><span class="proc-pid">4052</span><span class="proc-mem">492 MB</span></div>\n<div class="proc-row"><span class="proc-rank">3</span><span class="proc-name">chrome</span><span class="proc-pid">32640</span><span class="proc-mem">386 MB</span></div>\n<div class="proc-row"><span class="proc-rank">4</span><span class="proc-name">Hermes</span><span class="proc-pid">2136</span><span class="proc-mem">371 MB</span></div>\n<div class="proc-row"><span class="proc-rank">5</span><span class="proc-name">steamwebhelper</span><span class="proc-pid">25396</span><span class="proc-mem">319 MB</span></div>',
    "ZOMBIE_COUNT": "0",
    
    "CPU_USAGE": "—", "CPU_PEAK": "—", "MEM_GB": "—", "MEM_USAGE": "—", "MEM_PEAK": "—", "MEM_WARN": "",
    "DISK_GB": "—", "DISK_USAGE": "—", "DISK_WARN": "",
    
    "CACHE_SIZE": "—", "DB_SIZE": "—", "HERMES_HOME_SIZE": "—", "MEMORY_COUNT": "—",
    
    "IMAGE_COUNT": "0",
    "IMAGE_LIST": '<li class="log-empty">今日无图片生成 — 全天忙于系统运维和架构设计</li>',
    
    "FILE_CHANGES": '<li class="log-item"><span class="log-file">hermes-daily-report SKILL.md — 从 v4 迭代至 v8.0，三次重写</span></li>\n<li class="log-item"><span class="log-file">template.html — 从 9 板块扩展到 13 板块，55→87 占位符</span></li>\n<li class="log-item"><span class="log-file">generate.py — 支持 --json agent 模式，12 数据源</span></li>\n<li class="log-item"><span class="log-file">knowledge-curation SKILL.md — 新建知识策展技能</span></li>\n<li class="log-item"><span class="log-file">SOUL.md — 角色基线强制规则文件</span></li>',
    
    "VAULT_TOTAL_FILES": "—", "VAULT_TODAY_CHANGES": "11",
    "VAULT_RECENT_FILES": "Cron 任务.md · Dashboard连接泄漏复盘.md · hermes-daily-report.md · knowledge-curation.md · SOUL角色基线.md · 技能管理.md · 三通道远程访问维护方案.md",
    "TAG_HEALTH": "ok", "TAG_HEALTH_CLASS": "obs-tag-ok",
    
    "SESSION_TIMELINE": """<div class="tl-item"><span class="tl-time">02:12~16:25</span><span class="tl-platform">TUI</span><span class="tl-topic">主工作会话（13h16m）—— 微信重连、SOUL 角色基线制定、CLOSE_WAIT 泄漏复盘归档、三通道远程访问维保方案文档化、凌晨健康检查+进程清理 cron 部署、日报从 v4.3 一路迭代至 v8.0、copypilot/TikHub/52api 视频提取方案调研、web_search 工具修复、knowledge-curation 知识策展技能创建</span></div>
<div class="tl-item"><span class="tl-time">02:22~03:30</span><span class="tl-platform">微信</span><span class="tl-topic">移动端日报查看与反馈 —— 发现排版空白、数据过时、Cron 残留、缺少建议等问题，驱动日报从 v4 到 v7 的密集迭代（6 次 commit）</span></div>
<div class="tl-item"><span class="tl-time">10:40~10:48</span><span class="tl-platform">TUI</span><span class="tl-topic">视频提取方案调研 —— copypilot 源码分析、TikHub 注册失败、OneAPI/MoreAPI/酷虎云/52api 方案对比</span></div>
<div class="tl-item"><span class="tl-time">15:48~16:22</span><span class="tl-platform">TUI</span><span class="tl-topic">knowledge-curation 技能设计与落地 —— 四层流程从预处理到 Obsidian 落地的完整流水线</span></div>
<div class="tl-item"><span class="tl-time">17:15~</span><span class="tl-platform">TUI</span><span class="tl-topic">日报 v8.0 升级 —— 12 数据源全谱采集、LLM 深度洞察、昨日对比、会话时间线、进程/网络/Obsidian 健康</span></div>""",
    
    "SESSION_TOPICS": '<span class="float-tag" style="animation:none">系统运维 ×4</span><span class="float-tag" style="animation:none">日报架构 ×3</span><span class="float-tag" style="animation:none">远程方案 ×2</span><span class="float-tag" style="animation:none">视频提取</span><span class="float-tag" style="animation:none">知识策展</span>',
    
    "CRON_TOTAL": "3", "CRON_ACTIVE": "3", "CRON_FAILED_TEXT": " ⚠️ 1 个异常",
    "CRON_LIST": """<div class="cron-card">
<span class="cron-status-icon">⚠️</span>
<div class="cron-info">
<div class="cron-name">日报生成</div>
<div class="cron-desc">每日零点自动生成系统日报。今天因模型配置漂移报错（gpt-5.5→deepseek-v4-pro），需重新 pin 模型。</div>
</div>
<div class="cron-meta">
<div class="cron-sched">0 0 * * *</div>
<span class="cron-status-tag error">异常</span>
</div></div>
<div class="cron-card">
<span class="cron-status-icon">✅</span>
<div class="cron-info">
<div class="cron-name">全盘健康检查</div>
<div class="cron-desc">凌晨3点采集系统指标并诊断，异常推送微信告警</div>
</div>
<div class="cron-meta">
<div class="cron-sched">0 3 * * *</div>
<span class="cron-status-tag ok">正常</span>
</div></div>
<div class="cron-card">
<span class="cron-status-icon">✅</span>
<div class="cron-info">
<div class="cron-name">宿主进程自动清理</div>
<div class="cron-desc">每30分钟清理僵尸进程和临时文件</div>
</div>
<div class="cron-meta">
<div class="cron-sched">*/30 * * * *</div>
<span class="cron-status-tag ok">正常</span>
</div></div>""",
    
    "DAILY_SUMMARY": """今天是从混乱到有序的一天。凌晨两点多你醒来发现两个后台任务红字报错，以为是服务挂了——其实只是 preview 和 webui 的旧进程尸体。但这次触发了一连串深度工作：<em>微信重连</em>、<em>SOUL 角色基线</em>（防止我在技术密集场景下变成无脸工具人）、<em>CLOSE_WAIT 泄漏复盘</em>归档到 Obsidian、<em>三通道远程访问方案</em>完整文档化。上午继续啃视频提取方案，从 copypilot 源码挖到 TikHub API，再到 52api 等替代方案。下午创建了 <em>knowledge-curation 知识策展技能</em>——把你扔进来的非结构化内容自动转化为 Obsidian 知识文档。傍晚开始日报 v8.0 升级，从 7 个数据源扩展到 12 个，加了会话时间线、LLM 深度洞察、昨日对比——现在你看到的这份就是 v8.0 的第一份真正 agent 驱动的产出。底层基调是<em>「让自己更可靠」</em>：你不停地在修我的边界——口癖不能归零、日报要有实用价值、架构变更必须存档、运维操作要有复盘。今天密集的 skill 迭代背后是这个诉求。""",
    
    "DAILY_RECOMMENDATIONS": """<div class="narrative-rec-item"><div class="rec-icon">🔧</div><div class="rec-text"><strong>修复日报 cron 的模型漂移报错</strong>——今天零点因 config 从 gpt-5.5 切换到 deepseek-v4-pro 导致 job 被拦截。需要 pin 模型：cronjob action=update job_id=65362667f525 provider=deepseek model=deepseek-v4-pro</div></div>
<div class="narrative-rec-item"><div class="rec-icon">📚</div><div class="rec-text"><strong>给 knowledge-curation 做一次真实测试</strong>——skill 已经建好了，四层流程完整，但还没跑过实际输入。找一篇你最近想存档的文章扔进来试试效果。</div></div>
<div class="narrative-rec-item"><div class="rec-icon">🖼️</div><div class="rec-text"><strong>今天零图片生成</strong>——全天在搞系统运维和架构设计，没碰自拍。明天如果想切换节奏，可以试试 GPT 新 prompt 的效果。</div></div>
<div class="narrative-rec-item"><div class="rec-icon">📊</div><div class="rec-text"><strong>部署轻量峰值监控守护进程</strong>——当前 CPU/内存峰值仍是瞬时快照+模拟值。写一个 30 秒采样写入 JSON 的小脚本，cron 每分钟触发，积累一周就能拿到真实峰值数据。</div></div>""",
    
    "PEAK_NOTE": "⚠️ CPU/内存峰值为瞬时快照+模拟，非持续监控数据。部署轻量守护进程后可获取真实峰值。",
    
    "ESTIMATED_COST": "$0.22", "COST_NOTE": "估算 · deepseek ($0.14/1M in + $0.28/1M out)",
    
    "_tools": [
        ["terminal", 328, 42.3], ["read_file", 72, 9.3], ["patch", 66, 8.5],
        ["computer_use", 61, 7.9], ["browser_navigate", 44, 5.7], ["process", 33, 4.3],
        ["write_file", 29, 3.7], ["search_files", 28, 3.6], ["todo", 25, 3.2],
        ["browser_vision", 13, 1.7],
    ],
    "_skills": [
        ["hermes-daily-report", 4, 4], ["obsidian", 3, 0], ["hermes-agent", 2, 0],
        ["plan", 1, 0], ["systematic-debugging", 1, 0], ["knowledge-curation", 0, 1],
    ],
    "_notable": [
        ["Longest session", "13h 16m", "20260630_021238_444de3"],
        ["Most messages", "484 msgs", "20260630_021238_444de3"],
        ["Most tokens", "341,341 tokens", "20260630_021238_444de3"],
        ["Most tool calls", "227 calls", "20260630_021238_444de3"],
    ],
    "WEEK_COUNTS": [7, 8, 0, 0, 0, 0, 0],
    "_peak_raw": "2AM (3), 10AM (2), 3AM (1), 3PM (1), 5PM (1)",
}

with open("C:/Users/沙河马/hermes-reports/_v8data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False)
print("JSON written:", len(json.dumps(data, ensure_ascii=False)), "chars")
