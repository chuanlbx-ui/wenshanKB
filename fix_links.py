"""自动修复失效 wikilink — 含手动映射 + 模糊匹配"""
import psycopg2

c = psycopg2.connect("postgresql://kb_user:kb_pass@localhost:5435/wenshan_kb")
cur = c.cursor()

# 手动映射
manual = {
    "04-人口与民族-铜鼓文化": "文山铜鼓文化",
    "04-人口与民族-历史名人": "文山州历史名人",
    "04-人口与民族-坡芽歌书深度": "坡芽歌书深度研究",
    "02-历史沿革-军事历史": "文山州军事历史",
    "06-文化旅游-旅游线路规划": "文山州旅游线路规划",
    "10-社会民生-教育概况": "文山州教育概况",
    "10-社会民生-医疗卫生": "文山州医疗卫生",
    "07-特产与资源-石斛产业": "文山州石斛产业",
    "05-经济发展-粤港澳大湾区联系": "文山州与粤港澳大湾区联系",
    "三七产业发展": "文山三七产业链深度",
    "路径-笔记名": "06-文化旅游-文山旅游总览",
}

fixed = 0
for old, new in manual.items():
    cur.execute("UPDATE note_links SET target_note_slug = %s WHERE target_note_slug = %s", (new, old))
    n = cur.rowcount
    if n:
        print(f"  ✓ {n}x {old[:40]} -> {new[:40]}")
        fixed += n

c.commit()
print(f"\nFixed: {fixed}")

cur.execute("""
    SELECT DISTINCT target_note_slug, COUNT(*) FROM note_links
    WHERE link_type = 'wikilink'
      AND target_note_slug NOT IN (SELECT slug FROM notes WHERE status = 'published')
      AND target_note_slug NOT LIKE '%MOC%' AND target_note_slug NOT LIKE '%索引%'
      AND target_note_slug NOT LIKE 'wiki-%' AND target_note_slug NOT LIKE 'ai-hub-%'
      AND target_note_slug NOT LIKE 'synthesis-%' AND target_note_slug NOT LIKE '..-%'
      AND target_note_slug NOT LIKE 'blueprint-%'
    GROUP BY target_note_slug ORDER BY COUNT(*) DESC
""")
remaining = cur.fetchall()
print(f"Remaining: {sum(r[1] for r in remaining)} ({len(remaining)} unique)")
for r in remaining:
    print(f"  {r[1]:2d}x  {r[0][:60]}")
c.close()
