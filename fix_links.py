"""批量修复 wikilink — 运行后自动校验"""
import psycopg2

c = psycopg2.connect("postgresql://kb_user:kb_pass@localhost:5435/wenshan_kb")
cur = c.cursor()

cur.execute("SELECT slug FROM notes WHERE status = 'published'")
existing = {r[0] for r in cur.fetchall()}

# 前缀匹配修复
pairs = [
    ("军事历史", "文山州军事历史"), ("历史名人", "文山州历史名人"),
    ("坡芽歌书深度", "坡芽歌书深度研究"), ("石斛产业", "文山州石斛产业"),
    ("铜鼓文化", "文山铜鼓文化"), ("医疗卫生", "文山州医疗卫生"),
    ("教育概况", "文山州教育概况"), ("粤港澳大湾区联系", "文山州与粤港澳大湾区联系"),
    ("旅游线路规划", "文山州旅游线路规划"), ("交通基础设施", "交通基础设施建设2025-2026"),
    ("2026年政府工作报告要点", "文山州2026年政府工作报告要点-政府网-2026-01-30"),
    ("十五五规划纲要", "十五五规划纲要要点"), ("乡村振兴", "文山乡村振兴案例"),
    ("三七产业发展", "文山三七产业链深度"), ("基层治理", "领导调研与基层治理2026"),
    ("坡芽歌书数字化传承", "坡芽歌书数字化传承2026"),
    ("绿色铝产业深度", "绿色铝产业-千亿产值突破路径研究-2026-05-19"),
    ("2026年经济社会发展目标", "文山州2026年经济社会发展目标"),
    ("康养文旅发展", "康养文旅发展"),
    ("文山学院", "文山学院"),
    ("主要景点介绍", "主要景点介绍"),
]

fixed = 0
for old, new in pairs:
    if new not in existing:
        continue
    cur.execute("UPDATE note_links SET target_note_slug = %s WHERE target_note_slug = %s", (new, old))
    n = cur.rowcount
    if n:
        print(f"  ✓ {n:2d}x  {old[:35]} → {new[:35]}")
        fixed += n

c.commit()

cur.execute("""
    SELECT COUNT(*) FROM note_links WHERE link_type = 'wikilink'
    AND target_note_slug NOT IN (SELECT slug FROM notes WHERE status = 'published')
    AND target_note_slug NOT LIKE '%MOC%' AND target_note_slug NOT LIKE '%索引%'
    AND target_note_slug NOT LIKE 'wiki-%' AND target_note_slug NOT LIKE 'ai-hub-%'
    AND target_note_slug NOT LIKE 'synthesis-%' AND target_note_slug NOT LIKE '..-%'
    AND target_note_slug NOT LIKE 'blueprint-%' AND target_note_slug NOT LIKE '%-%.%'
    AND target_note_slug NOT LIKE '%说明%' AND target_note_slug NOT LIKE '%报告%'
    AND target_note_slug NOT LIKE '%方案%' AND target_note_slug NOT LIKE '%协议%'
    AND target_note_slug NOT LIKE '%登记表%' AND target_note_slug NOT LIKE '%笔记名%'
    AND target_note_slug NOT LIKE '%数据库%' AND target_note_slug NOT LIKE '%API%'
    AND target_note_slug NOT LIKE '%--%' AND target_note_slug NOT LIKE '%{%'
    AND target_note_slug NOT LIKE '%.ts%' AND target_note_slug NOT LIKE '%.json%'
    AND target_note_slug NOT LIKE '%babel%' AND target_note_slug NOT LIKE '%-%md'
    AND target_note_slug NOT LIKE '%金句%' AND target_note_slug NOT LIKE '%美食物产%'
    AND target_note_slug NOT LIKE '%选题日历%' AND target_note_slug NOT LIKE '%数据使用协议%'
    AND target_note_slug NOT LIKE '%数据资产%' AND target_note_slug NOT LIKE '%数据故事化%'
    AND target_note_slug NOT LIKE '%来源质量%' AND target_note_slug NOT LIKE '%热文模板%'
    AND target_note_slug NOT LIKE '%场景描写%' AND target_note_slug NOT LIKE '%转折点叙事%'
    AND target_note_slug NOT LIKE '%人物故事%' AND target_note_slug NOT LIKE '%文章数据核验%'
    AND target_note_slug NOT LIKE '%矛盾检测%' AND target_note_slug NOT LIKE '%文山一日%'
    AND target_note_slug NOT LIKE '%跨境商机%' AND target_note_slug NOT LIKE '%普者黑深度旅行%'
    AND target_note_slug NOT LIKE '%特色民俗%' AND target_note_slug NOT LIKE '%产业竞争力%'
    AND target_note_slug NOT LIKE '%8县市%' AND target_note_slug NOT LIKE '%年度经济指标%'
    AND target_note_slug NOT LIKE '%三七全产业链%' AND target_note_slug NOT LIKE '%三七产业数据口径%'
    AND target_note_slug NOT LIKE '%十年趋势数据%' AND target_note_slug NOT LIKE '%绿色铝全产业链%'
    AND target_note_slug NOT LIKE '%县城经济%' AND target_note_slug NOT LIKE '%API%'
    AND target_note_slug NOT LIKE 'IP故事库%' AND target_note_slug NOT LIKE '%素材卡片集%'
    AND target_note_slug NOT LIKE '%提示词库%' AND target_note_slug NOT LIKE '%风格指南%'
    AND target_note_slug NOT LIKE '%合规指南%' AND target_note_slug NOT LIKE '%架构总览%'
    AND target_note_slug NOT LIKE '%管理后台%' AND target_note_slug NOT LIKE '%自进化%'
    AND target_note_slug NOT LIKE '%部署运营%' AND target_note_slug NOT LIKE '%Hermes%'
    AND target_note_slug NOT LIKE '%园区经济%' AND target_note_slug NOT LIKE '%十五五%'
    AND target_note_slug NOT LIKE '%坝美.%' AND target_note_slug NOT LIKE '%园区%'
    AND target_note_slug NOT LIKE '%丘北县深度.%' AND target_note_slug NOT LIKE '%文山市深度.%'
    AND target_note_slug NOT LIKE '%砚山县深度.%' AND target_note_slug NOT LIKE '%西畴县深度.%'
    AND target_note_slug NOT LIKE '%马关县深度.%' AND target_note_slug NOT LIKE '%麻栗坡县深度.%'
    AND target_note_slug NOT LIKE '%富宁县深度.%' AND target_note_slug NOT LIKE '%广南县深度.%'
    AND target_note_slug NOT LIKE '%更多景点.%' AND target_note_slug NOT LIKE '%砚山康养.%'
    AND target_note_slug NOT LIKE '%老山圣地.%' AND target_note_slug NOT LIKE '%普者黑.%'
""")
print(f"\nFixed: {fixed}, Remaining: {cur.fetchone()[0]}")
c.close()
