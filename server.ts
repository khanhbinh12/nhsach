import express from 'express';
import path from 'path';
import { fileURLToPath } from 'url';
import { spawn, ChildProcess } from 'child_process';
import dotenv from 'dotenv';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT ? parseInt(process.env.PORT, 10) : 3000;
const PYTHON_PORT = 5001;
const isProduction = process.env.NODE_ENV === 'production';

// Support JSON bodies for API
app.use(express.json());

// Spawn Python OOP backend
let pythonProcess: ChildProcess | null = null;

function startPythonBackend() {
  const pythonScript = path.join(__dirname, 'backend', 'server.py');
  console.log(`[Node Server] Đang khởi động Python OOP backend tại port ${PYTHON_PORT}...`);

  pythonProcess = spawn('python3', [pythonScript, String(PYTHON_PORT)], {
    stdio: 'inherit',
    env: { ...process.env, PYTHONUNBUFFERED: '1' }
  });

  pythonProcess.on('exit', (code, signal) => {
    console.warn(`[Node Server] Python backend thoát với code ${code}, tín hiệu ${signal}. Khởi động lại sau 2s...`);
    setTimeout(startPythonBackend, 2000);
  });
}

startPythonBackend();

// Proxy API requests to Python OOP backend with retry
app.all('/api/*', async (req, res) => {
  const targetUrl = `http://127.0.0.1:${PYTHON_PORT}${req.originalUrl}`;
  
  const forwardHeaders: Record<string, string> = {
    'Content-Type': req.headers['content-type'] || 'application/json'
  };

  const options: RequestInit = {
    method: req.method,
    headers: forwardHeaders
  };

  if (['POST', 'PUT', 'PATCH'].includes(req.method)) {
    options.body = JSON.stringify(req.body);
  }

  // Attempt fetch with up to 3 quick retries for cold start
  for (let attempt = 1; attempt <= 3; attempt++) {
    try {
      const response = await fetch(targetUrl, options);
      const data = await response.text();
      res.status(response.status);
      res.setHeader('Content-Type', response.headers.get('content-type') || 'application/json');
      return res.send(data);
    } catch (err) {
      if (attempt === 3) {
        console.error(`[Proxy Error] Lỗi kết nối tới Python backend tại ${targetUrl}:`, err);
        return res.status(502).json({
          success: false,
          error: 'Không thể kết nối đến máy chủ Python OOP backend. Vui lòng thử lại sau giây lát.'
        });
      }
      await new Promise(r => setTimeout(r, 400));
    }
  }
});

// Setup Vite middleware in dev or static files in production
async function setupVite() {
  if (!isProduction) {
    const { createServer: createViteServer } = await import('vite');
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa'
    });
    app.use(vite.middlewares);
    console.log('[Node Server] Vite middleware đã được gắn thành công.');
  } else {
    const distPath = path.join(__dirname, 'dist');
    app.use(express.static(distPath));
    app.get('*', (_req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`[Bookstore System] Máy chủ web đang chạy tại http://0.0.0.0:${PORT}`);
  });
}

setupVite().catch((err) => {
  console.error('[Node Server] Lỗi khởi động máy chủ:', err);
  process.exit(1);
});
