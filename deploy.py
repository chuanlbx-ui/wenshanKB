"""文山KB 部署 — 最终安全方案"""
import paramiko, time

HOST = "162.14.114.224"
USER = "root"
PASS = "simonYC6531))"
DOMAIN = "wskb.wenbita.cn"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASS, timeout=15)

def run(cmd, timeout=60):
    print(f">>> {cmd[:120]}")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors='replace')
    err = stderr.read().decode(errors='replace')
    if out.strip(): print(out.strip()[:400])
    if err.strip(): print(f"E: {err.strip()[:200]}")
    return out

# 1. Start pgvector on port 5433
print("=== 1. PG+pgvector (port 5433) ===")
run("docker rm -f wenshan-pg 2>&1")
run("docker run -d --name wenshan-pg -e POSTGRES_USER=kb_user -e POSTGRES_PASSWORD=kb_pass -e POSTGRES_DB=wenshan_kb -p 5433:5432 pgvector/pgvector:pg16 2>&1", timeout=120)
time.sleep(5)
run("docker exec wenshan-pg psql -U kb_user -d wenshan_kb -c 'CREATE EXTENSION IF NOT EXISTS vector;' 2>&1", timeout=15)
run("cat /opt/wenshan-kb/blueprint/mvp/db_schema.sql | docker exec -i wenshan-pg psql -U kb_user -d wenshan_kb 2>&1 | tail -5", timeout=30)

# 2. Create .env
print("\n=== 2. Config ===")
env = f"""DATABASE_URL=postgresql+asyncpg://kb_user:kb_pass@localhost:5433/wenshan_kb
DATABASE_URL_SYNC=postgresql://kb_user:kb_pass@localhost:5433/wenshan_kb
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=wskb-prod-{int(time.time())}
AGENT_API_KEY=wskb-agent-prod-key
LLM_API_KEY=sk-b8a70bb4eb80473fa21912302b0c90bc
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
EMBEDDING_API_KEY=sk-ospyolrjjrbvpdtumkyrcruyitwbambrphaqqakgqjgdeixp
EMBEDDING_BASE_URL=https://api.siliconflow.cn/v1
EMBEDDING_MODEL=BAAI/bge-large-zh-v1.5
CORS_ORIGINS=*
"""
run(f"cat > /opt/wenshan-kb/.env << 'ENVEOF'\n{env}\nENVEOF")

# 3. Run migration
print("\n=== 3. Migration ===")
run("cd /opt/wenshan-kb && DATABASE_URL='postgresql+asyncpg://kb_user:kb_pass@localhost:5433/wenshan_kb' python3 -m app.migration.runner --source . --mode full 2>&1 | tail -15", timeout=180)

# 4. Start API
print("\n=== 4. API ===")
run("pkill -f uvicorn 2>&1; sleep 1")
start_script = """#!/bin/bash
cd /opt/wenshan-kb
export DATABASE_URL='postgresql+asyncpg://kb_user:kb_pass@localhost:5433/wenshan_kb'
exec python3 -c "import sys; sys.path.insert(0,'api'); from dotenv import load_dotenv; load_dotenv('.env'); import uvicorn; uvicorn.run('app.main:app',host='0.0.0.0',port=8000)"
"""
run(f"cat > /opt/wenshan-kb/start_api.sh << 'SH'\n{start_script}\nSH")
run("chmod +x /opt/wenshan-kb/start_api.sh")
client.exec_command("cd /opt/wenshan-kb && nohup bash start_api.sh > /tmp/wenshan-api.log 2>&1 &")
time.sleep(4)

# 5. Nginx
print("\n=== 5. Nginx ===")
conf = f"""server {{
    listen 80;
    server_name {DOMAIN};
    location / {{
        root /opt/wenshan-kb/site;
        index index.html;
        try_files $uri $uri/ /index.html;
    }}
    location /api/ {{
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 60s;
    }}
    location /docs {{
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }}
    location /static/ {{
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }}
    client_max_body_size 50M;
}}"""
run(f"cat > /www/server/nginx/conf/vhost/wenshan-kb.conf << 'NGX'\n{conf}\nNGX")
run("/www/server/nginx/sbin/nginx -t 2>&1")
run("/www/server/nginx/sbin/nginx -s reload 2>&1")

# 6. Verify
print("\n=== 6. Verify ===")
time.sleep(2)
run("cat /tmp/wenshan-api.log 2>&1 | tail -10")
run("curl -s http://localhost:8000/api/v1/notes?page_size=1 2>&1 | python3 -c \"import sys,json;d=json.load(sys.stdin);print('Notes:', d.get('pagination',{}).get('total','ERROR'))\" 2>&1")

print(f"\n===========================================")
print(f"  Site: http://{DOMAIN}/")
print(f"  API:  http://{DOMAIN}/api/v1/health")
print(f"  Docs: http://{DOMAIN}/docs")
print(f"  Start: /opt/wenshan-kb/start_api.sh")
print(f"===========================================")

client.close()
