# EcoSync Deployment Guide - Render + Vercel

## Architecture
```
Browser → Vercel (always awake)
           ├── /             → Next.js frontend
           ├── /api/proxy/*  → Proxied to Render backend
           └── /api/cron/wake → Pings Render every 5 min (keeps it awake)
```

---

## Step 1: Deploy Backend to Render

1. Go to **https://dashboard.render.com/new/web-service**
2. Configure:
   | Field | Value |
   |-------|-------|
   | **Name** | `ecosync-api` |
   | **Language** | `Python` |
   | **Root Directory** | (leave empty) |
   | **Branch** | `main` |

3. **Build Command:**
   ```
   pip install -r backend/requirements.txt
   ```

4. **Start Command:**
   ```
   uvicorn backend.main:app --host 0.0.0.0 --port $PORT
   ```

5. **Instance Type:** `Free`

6. **Environment Variables:**
   ```
   CORS_ORIGINS=https://ecosync.vercel.app,http://localhost:3000
   PYTHON_VERSION=3.11
   ```

7. Click **"Create Web Service"**

⏱ Wait 3-5 mins. Copy the URL (e.g. `https://ecosync-api.onrender.com`)

---

## Step 2: Deploy Frontend to Vercel

1. Go to **https://vercel.com** → New Project → Import `EcoSync`
2. Set **Root Directory**: `frontend`
3. **Environment Variables:**
   ```
   NEXT_PUBLIC_API_URL=/api/proxy
   BACKEND_URL=https://ecosync-api.onrender.com
   NEXT_PUBLIC_WS_URL=wss://ecosync-api.onrender.com
   ```
   ⚠️ Replace with your actual Render URL
4. Click **Deploy**

---

## Step 3: Update Render CORS

After Vercel deploys, go to Render → Your Service → Environment and update:
```
CORS_ORIGINS=https://ecosync-xxx.vercel.app,http://localhost:3000
```
Then **Save Changes** → **Manual Deploy** → **Deploy latest commit**

---

## Done!

🌐 Live at: `https://ecosync-xxx.vercel.app`
⏰ Always awake: Vercel cron pings Render every 5 min
