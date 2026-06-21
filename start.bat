@echo off
echo ============================
echo   文山州知识库 - 一键启动
echo ============================

echo.
echo [1/4] 启动数据库和 Redis...
docker compose up -d db redis
timeout /t 5 /nobreak >nul

echo [2/4] 等待数据库就绪...
:wait_db
docker compose ps db | findstr "healthy" >nul
if errorlevel 1 (
    timeout /t 3 /nobreak >nul
    goto wait_db
)
echo   数据库已就绪！

echo [3/4] 启动 API 服务...
start "WenShanKB-API" python -c "import sys,os; sys.path.insert(0,'api'); os.environ['DATABASE_URL']='postgresql+asyncpg://kb_user:kb_pass@localhost:5435/wenshan_kb'; from dotenv import load_dotenv; load_dotenv('.env'); import uvicorn; uvicorn.run('app.main:app',host='0.0.0.0',port=8000,log_level='warning')"

echo [4/4] 启动前端...
start "WenShanKB-Web" cmd /c "npm --prefix web run dev"

echo.
echo ============================
echo   启动完成！
echo   前端: http://localhost:3001
echo   API:  http://localhost:8000/docs
echo   仪表盘: http://localhost:3001
echo ============================
pause
