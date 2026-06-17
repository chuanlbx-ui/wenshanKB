"""给所有已发布笔记生成向量嵌入"""
import asyncio, sys, os

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
        print("EMBEDDING_API_KEY not set")
        return

    client = AsyncOpenAI(api_key=settings.EMBEDDING_API_KEY, base_url=settings.EMBEDDING_BASE_URL)
    engine = create_async_engine(settings.DATABASE_URL)

    async with AsyncSession(engine) as db:
        result = await db.execute(
            text("SELECT id, title, plain_text FROM notes WHERE status = 'published' AND embedding IS NULL LIMIT 300")
        )
        rows = result.fetchall()
        print(f"需要生成: {len(rows)} 篇")

        count = 0
        for r in rows:
            note_id, title, plain = r
            input_text = (plain or title)[:8000]
            if len(input_text) < 20:
                continue

            try:
                resp = await client.embeddings.create(
                    model=settings.EMBEDDING_MODEL, input=input_text, encoding_format="float"
                )
                vec = resp.data[0].embedding
                if len(vec) < 1536:
                    vec = vec + [0.0] * (1536 - len(vec))
                vec_str = "[" + ",".join(f"{v:.8f}" for v in vec) + "]"

                await db.execute(text("UPDATE notes SET embedding = :vec WHERE id = :id"), {"vec": vec_str, "id": note_id})
                count += 1
                await asyncio.sleep(0.3)  # 避免 API 限流
                if count % 5 == 0:
                    await db.commit()
                    print(f"  {count}/{len(rows)} - {title[:30]}")
            except Exception as e:
                print(f"  FAIL {title[:30]}: {e}")
                continue

        await db.commit()
        print(f"\nDONE: {count} 篇")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
