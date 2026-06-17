"""批量生成向量嵌入 — 直接 API 调用版"""
import asyncio, sys, os, time

from dotenv import load_dotenv
load_dotenv()
os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL", "").replace("db:5432", "localhost:5435")
sys.path.insert(0, "api")

from app.config import get_settings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
from openai import AsyncOpenAI

settings = get_settings()

async def main():
    if not settings.EMBEDDING_API_KEY:
        print("No key"); return

    client = AsyncOpenAI(api_key=settings.EMBEDDING_API_KEY, base_url=settings.EMBEDDING_BASE_URL)
    engine = create_async_engine(settings.DATABASE_URL)

    async with AsyncSession(engine) as db:
        r = await db.execute(
            text("SELECT id, title, plain_text FROM notes WHERE status = 'published' AND embedding IS NULL LIMIT 300")
        )
        rows = r.fetchall()
        print(f"Remaining: {len(rows)}")

        ok, skip = 0, 0
        t0 = time.time()
        for r in rows:
            nid, title, plain = r
            txt = (plain or title)[:500]  # SiliconFlow 限制 ≤512 tokens
            if len(txt) < 20: continue

            try:
                resp = await client.embeddings.create(
                    model=settings.EMBEDDING_MODEL,
                    input=txt,
                    encoding_format="float"
                )
                vec = resp.data[0].embedding
                if len(vec) < 1536:
                    vec = vec + [0.0] * (1536 - len(vec))
                vec_str = "[" + ",".join(f"{v:.8f}" for v in vec) + "]"
                await db.execute(text("UPDATE notes SET embedding = :vec WHERE id = :id"), {"vec": vec_str, "id": nid})
                ok += 1
            except Exception as e:
                skip += 1
                if skip <= 3:
                    print(f"  ERR {title[:30]}: {e}")

            if (ok + skip) % 10 == 0:
                await db.commit()
                el = time.time() - t0
                print(f"  [{ok + skip}/{len(rows)}] ok={ok} skip={skip} | {el:.0f}s")

            # 关键：限速！免费 API 每分钟 60 次
            await asyncio.sleep(0.8)

        await db.commit()
        print(f"\nDone: ok={ok} skip={skip}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
