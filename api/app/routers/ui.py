from fastapi import APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

router = APIRouter()

HTML = """<!doctype html>
<html lang="pt">
<head>
  <meta charset="utf-8">
  <title>ML Trade – UI mínima</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    :root { font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial; }
    body { margin: 24px; line-height: 1.35; }
    h1 { margin: 0 0 16px; }
    section { border: 1px solid #ddd; padding: 16px; border-radius: 8px; margin: 16px 0; }
    label { display:block; margin: 6px 0 2px; font-size: 0.9rem; }
    input, select { width: 100%; padding: 8px; box-sizing: border-box; }
    .row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    button { padding: 10px 14px; border: 1px solid #333; background: #111; color: #fff; border-radius: 6px; cursor: pointer; }
    button.secondary { background: #fff; color: #111; }
    .muted { color:#666; font-size: .9rem; }
    .links a { margin-right: 12px; }
  </style>
</head>
<body>
  <h1>ML Trade – UI mínima</h1>
  <div class="links">
    <a href="/docs" target="_blank">Swagger /docs</a>
    <a href="/redoc" target="_blank">ReDoc /redoc</a>
    <a href="/ui/health" target="_blank">/ui/health</a>
  </div>

  <section>
    <h2>/dataset (diário e intraday)</h2>
    <div class="row">
      <div>
        <label>Símbolo</label>
        <input id="ds-symbol" value="ASML.AS">
      </div>
      <div>
        <label>Timeframe (ex: 1d, 1h, 15m)</label>
        <input id="ds-tf" value="1h">
      </div>
    </div>
    <label>Colunas (vírgulas)</label>
    <input id="ds-cols" value="time,close,rsi14,sma20,hlc3">
    <div class="row" style="margin-top:12px;">
      <button onclick="openDataset()">Abrir /dataset em nova aba</button>
      <button class="secondary" onclick="openDatasetCSV()">Descarregar /dataset/csv</button>
    </div>
    <p class="muted">Para diário, o backend ignora limit/offset. Para intraday, podes usar dropna=true e decimals=4.</p>
  </section>

  <section>
    <h2>/feature-store/dataset (com cache/TTL)</h2>
    <div class="row">
      <div>
        <label>Limit</label>
        <input id="fs-limit" type="number" value="5">
      </div>
      <div>
        <label>Dropna</label>
        <select id="fs-dropna">
          <option value="false" selected>false</option>
          <option value="true">true</option>
        </select>
      </div>
    </div>
    <div class="row" style="margin-top:12px;">
      <button onclick="openFS()">Abrir /feature-store/dataset</button>
      <button class="secondary" onclick="openProvidersDiag()">Abrir /providers/diag</button>
    </div>
  </section>

  <script>
    function enc(v){ return encodeURIComponent(v.trim()); }

    function openDataset(){
      const s = document.getElementById('ds-symbol').value;
      const tf = document.getElementById('ds-tf').value;
      const cols = document.getElementById('ds-cols').value;
      const url = `/dataset/?symbol=${enc(s)}&tf=${enc(tf)}&columns=${enc(cols)}&dropna=true&decimals=4`;
      window.open(url, '_blank');
    }
    function openDatasetCSV(){
      const s = document.getElementById('ds-symbol').value;
      const tf = document.getElementById('ds-tf').value;
      const cols = document.getElementById('ds-cols').value;
      const url = `/dataset/csv?symbol=${enc(s)}&tf=${enc(tf)}&columns=${enc(cols)}&decimals=4`;
      window.open(url, '_blank');
    }
    function openFS(){
      const s = document.getElementById('ds-symbol').value;
      const tf = document.getElementById('ds-tf').value;
      const cols = document.getElementById('ds-cols').value;
      const limit = document.getElementById('fs-limit').value;
      const dropna = document.getElementById('fs-dropna').value;
      const url = `/feature-store/dataset?symbol=${enc(s)}&tf=${enc(tf)}&columns=${enc(cols)}&limit=${enc(limit)}&dropna=${enc(dropna)}`;
      window.open(url, '_blank');
    }
    function openProvidersDiag(){
      const s = document.getElementById('ds-symbol').value;
      const tf = document.getElementById('ds-tf').value;
      const url = `/providers/diag?symbol=${enc(s)}&tf=${enc(tf)}`;
      window.open(url, '_blank');
    }
  </script>
</body>
</html>
"""

@router.get("/ui", response_class=HTMLResponse)
def ui_root() -> HTMLResponse:
    return HTMLResponse(content=HTML)

@router.get("/ui/health")
def ui_health() -> JSONResponse:
    return JSONResponse({"status": "ok"})

@router.get("/ui/docs")
def ui_docs():
    # atalho conveniente
    return RedirectResponse(url="/docs")
