# 圖書館視聽中心環景導覽 3.0

以 [Marzipano](https://www.marzipano.net/) 製作的圖書館視聽中心 360° 環景導覽網站，共 19 個場景，可透過熱點在各區域間移動。

## 場景列表

| # | 場景 ID | 名稱 |
|---|---------|------|
| 0 | `0-` | 工學院出入口 |
| 1 | `1-` | 工學院出入口 |
| 2 | `2-` | 視聽中心電梯口 |
| 3 | `3-` | 放映室一二三 |
| 4 | `4-` | 電視區 |
| 5 | `5-` | 電視區 |
| 6 | `6-` | 電腦區入口 |
| 7 | `7-` | 電腦區 |
| 8 | `8-video` | VIDEO 走廊前 |
| 9 | `9-video` | VIDEO 走廊中 |
| 10 | `10-video` | VIDEO 走廊後 |
| 11 | `11-` | 放映室五六 |
| 12 | `12-` | 放映室五六 |
| 13 | `13-slides-` | SLIDES 幻燈片區 |
| 14 | `14---` | 洗手間 / 茶水間 |
| 15 | `15-vr` | VR 體驗區 |
| 16 | `16-` | 媒體借還櫃檯 |
| 17 | `17-` | 媒體資料區 |
| 18 | `18-` | 館藏查詢區 |

## 專案結構

```
.
├── index.html   # 頁面骨架、場景選單與控制按鈕
├── index.js     # 檢視器初始化、場景切換、熱點與自動旋轉邏輯
├── data.js      # 場景資料（APP_DATA）：視角、熱點、tile 層級與全域設定
├── style.css    # 介面樣式（含桌機 / 手機響應式）
├── vendor/      # ⚠️ 尚未上傳：marzipano.js、screenfull.min.js、bowser.min.js、reset.min.css
├── img/         # ⚠️ 尚未上傳：控制按鈕與熱點圖示
└── tiles/       # ⚠️ 尚未上傳：各場景的環景切片圖（tiles/<場景ID>/...）
```

> **注意：** 目前 repo 只有 4 個主要檔案，`vendor/`、`img/`、`tiles/` 三個資料夾還沒上傳，網站無法正常顯示。
> 請把 Marzipano Tool 匯出的完整資料夾內容一起加入 repo。

## 本機預覽

環景切片需透過 HTTP 載入，不能直接雙擊開啟 `index.html`。在專案資料夾執行任一指令：

```bash
python3 -m http.server 8000
# 或
npx serve .
```

再用瀏覽器開啟 <http://localhost:8000>。

## 修改設定

全域設定位於 `data.js` 最下方的 `settings`：

| 設定 | 目前值 | 說明 |
|------|--------|------|
| `mouseViewMode` | `drag` | 滑鼠操作方式（`drag` 拖曳 / `qtvr`） |
| `autorotateEnabled` | `true` | 是否自動旋轉 |
| `fullscreenButton` | `true` | 是否顯示全螢幕按鈕 |
| `viewControlButtons` | `false` | 是否顯示上下左右／縮放按鈕 |

## 部署到 GitHub Pages

1. 確認 `vendor/`、`img/`、`tiles/` 都已上傳。
2. 到 repo 的 **Settings → Pages**，Source 選 `main` 分支、`/ (root)`。
3. 儲存後即可在 `https://<帳號>.github.io/<repo>/` 瀏覽。

## 授權

`index.js` 與 `style.css` 源自 Marzipano Tool 範本（© Google Inc.，Apache License 2.0）。
