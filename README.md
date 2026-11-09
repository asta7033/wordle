# 雲端技術與應用期中 Wordle

## 功能
- 任務一：第 6 次猜錯時，後端回傳 `target_word`，前端顯示 `Game Over! The word was XXXXX. Press R to restart.`；每次猜錯顯示 `Keep guessing! (N tries left)`
- 任務二：不在 `WORD_BANK` 的字回傳 HTTP 400 `Word not in dictionary`，前端顯示 `Not in word list!`，不消耗次數，可用 Backspace 修改
- 任務三：視窗寬 700，右側（x 500~700）顯示本局猜測歷史；`GET /api/stats`，新局和猜測的回應也帶 `stats`；右上角顯示 `Total: X | Wins: Y | Win Rate: Z%`
- 任務四：`POST /api/new-game` 可帶 `{"hard_mode": true}`（預設 False）；困難模式下綠色字母必須留在原位，否則回傳 400；按 `H` 切換模式並開新局，右上角顯示 `Mode: Normal` / `Mode: HARD`

## 本機執行
```bash
pip install -r requirements.txt
python server.py
```
另開一個終端機（PowerShell）：
```powershell
$env:API_BASE_URL="http://127.0.0.1:8000"; python client.py
```

## Render 部署
1. New → Web Service → 選這個 GitHub repo
2. Build Command：`pip install -r requirements.txt`
3. Start Command：`uvicorn server:app --host 0.0.0.0 --port $PORT`
4. 部署完成後把 `client.py` 的 `API_BASE_URL` 預設值換成 Render 網址再 commit push
```bash
 ／|_
（ﾟω ｡ 7
  |    \
  しし__,)ノ

