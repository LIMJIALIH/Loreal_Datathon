# CORS & Environment Configuration Guide

## 🔧 Changes Made

### Backend (api.py)
Updated CORS configuration to allow requests from:
- ✅ `http://localhost:3000` - Local frontend development
- ✅ `http://localhost:5000` - Local backend
- ✅ `https://loreal-datathon.vercel.app` - Production frontend
- ✅ `https://loreal-datathon.onrender.com` - Production backend
- ✅ `https://*.vercel.app` - All Vercel preview deployments

### Frontend Environment Files

**`.env.local`** (Development - not committed)
```bash
NEXT_PUBLIC_API_URL=https://loreal-datathon.onrender.com/api
```

**`.env.production`** (Production)
```bash
NEXT_PUBLIC_API_URL=https://loreal-datathon.onrender.com/api
```

**`.env.example`** (Template)
```bash
NEXT_PUBLIC_API_URL=http://localhost:5000/api
```

## 🚀 Deployment Steps

### 1. Redeploy Backend to Render
Your updated CORS configuration has been pushed to GitHub. Render will automatically redeploy:

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Find your `loreal-datathon` service
3. Wait for auto-deploy to complete (or manually trigger deploy)
4. Verify deployment at: https://loreal-datathon.onrender.com/api/metrics

### 2. Update Frontend on Vercel
Your Vercel deployment should use the production environment variables:

**Option A: Vercel will auto-detect `.env.production`**
- Just push the code (already done ✅)
- Vercel uses `.env.production` automatically

**Option B: Set in Vercel Dashboard (Recommended)**
1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Select your project
3. Go to **Settings** → **Environment Variables**
4. Add/Update:
   - Variable: `NEXT_PUBLIC_API_URL`
   - Value: `https://loreal-datathon.onrender.com/api`
   - Environments: `Production`, `Preview`, `Development`
5. Redeploy

### 3. Test CORS
Once both are deployed, test the connection:

```bash
# Should return data without CORS errors
curl https://loreal-datathon.vercel.app
```

Or open browser console at your Vercel URL and check for CORS errors.

## 🐛 Troubleshooting

### Still Getting CORS Errors?

1. **Check Render Logs**
   ```
   Dashboard → Your Service → Logs
   ```
   Look for CORS-related messages

2. **Verify Environment Variables**
   - Vercel: Settings → Environment Variables
   - Check `NEXT_PUBLIC_API_URL` is correct

3. **Clear Browser Cache**
   - Hard refresh: `Ctrl+Shift+R` (Windows) or `Cmd+Shift+R` (Mac)
   - Or clear cache in DevTools

4. **Check Network Tab**
   - Open DevTools → Network
   - Look for OPTIONS preflight request
   - Should see `Access-Control-Allow-Origin` header

### Backend Not Updating?

1. **Force Redeploy on Render**
   ```
   Dashboard → Your Service → Manual Deploy → Deploy latest commit
   ```

2. **Check Deployment Logs**
   - Ensure no errors during deployment
   - Verify the new code is deployed

### Frontend Not Using Production URL?

1. **Verify `.env.production` is being used**
   ```bash
   # In frontend directory
   npm run build
   ```
   Check build output for environment variable

2. **Set in Vercel Dashboard** (most reliable)
   - Always set environment variables in Vercel UI
   - Redeploy after adding variables

## 🧪 Testing Locally

To test CORS locally before deploying:

```bash
# Terminal 1 - Backend
cd backend
python api.py

# Terminal 2 - Frontend
cd frontend
npm run dev
```

Visit `http://localhost:3000` - should connect to backend without CORS errors.

## 📝 Notes

- ✅ CORS is configured in `backend/api.py`
- ✅ Changes pushed to GitHub
- ⏳ Render will auto-deploy (5-10 minutes)
- ⏳ Vercel needs environment variable set (if not using `.env.production`)

## 🎉 Once Complete

Your app will be fully functional:
- Frontend: https://loreal-datathon.vercel.app
- Backend: https://loreal-datathon.onrender.com

No more CORS errors! 🚀
