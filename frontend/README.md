# Crawl4AI - WeChat Console Frontend

Modern React + TypeScript frontend for the WeChat Article Crawler task management system.

## Tech Stack

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool & dev server
- **Ant Design** - UI component library
- **React Router** - Routing
- **TanStack Query** - Data fetching & caching
- **Axios** - HTTP client
- **Day.js** - Date formatting

## Quick Start

### Development Mode

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Frontend will be available at: http://localhost:5173
```

### Production Build

```bash
# Build for production
npm run build

# Preview production build locally
npm run preview

# Output will be in dist/ directory
```

## Configuration

### Development (.env)

```env
VITE_API_BASE_URL=http://localhost:11235
```

### Production (.env.production)

```env
# Empty = uses same origin (Nginx proxy)
VITE_API_BASE_URL=
```

For standalone deployment without Nginx proxy:

```env
VITE_API_BASE_URL=http://your-backend-server:11235
```

## Features

✅ Task Management (create, edit, delete, pause/resume)
✅ File Upload (Excel/CSV with WeChat URLs)
✅ Schedule Configuration (once, interval, cron)
✅ Execution History
✅ Data Export (Excel/CSV/JSON)
✅ Real-time Statistics

## Pages

- `/` - Task List Dashboard
- `/tasks/create` - Create New Task (3-step wizard)
- `/tasks/:id` - Task Detail & History

## Docker Deployment

### With Docker Compose

1. Build the frontend:

```bash
npm install
npm run build
```

2. Enable frontend service in `docker-compose.yml` (uncomment lines 92-109)

3. Start all services:

```bash
cd ..  # Go to project root
docker compose up -d
```

4. Access frontend at http://localhost:8080

### Standalone Nginx Deployment

```bash
# Build frontend
npm run build

# Copy to Nginx
cp -r dist/* /usr/share/nginx/html/

# Use provided Nginx config
cp ../deploy/docker/nginx.conf /etc/nginx/nginx.conf

# Reload Nginx
nginx -s reload
```

## Development

### File Structure

```
src/
├── api/           # API client and types
│   └── client.ts  # Axios client with all API methods
├── pages/         # Page components
│   ├── TaskList.tsx       # Main dashboard
│   ├── TaskCreate.tsx     # 3-step wizard
│   └── TaskDetail.tsx     # Task details & history
├── types/         # TypeScript definitions
│   └── index.ts   # Task, Article, Execution types
├── App.tsx        # Main app with routing
├── App.css        # Global styles
└── main.tsx       # Entry point
```

### Adding New Features

1. Update types in `src/types/index.ts`
2. Add API methods in `src/api/client.ts`
3. Create/update page components
4. Add routes in `App.tsx`

### Code Style

- Use TypeScript strict mode
- Follow React hooks best practices
- Use TanStack Query for data fetching
- Use Ant Design components
- Keep components focused and single-purpose

## Troubleshooting

### Backend Connection Issues

If frontend can't connect to backend:

1. Check backend is running:
```bash
curl http://localhost:11235/health
```

2. Check CORS is enabled in backend (`server.py`)

3. Verify API URL in browser console (Network tab)

### Build Errors

```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Clear Vite cache
rm -rf node_modules/.vite
npm run build
```

### Port Already in Use

```bash
# Change port in vite.config.ts
export default defineConfig({
  server: {
    port: 5174  // Use different port
  }
})
```

## Performance

### Production Optimizations

- Vite automatically code-splits by route
- Images and assets are optimized
- Gzip compression enabled in Nginx
- Long cache for static assets (1 year)
- No cache for index.html (ensures updates)

### Monitoring

```bash
# Analyze bundle size
npm run build -- --mode analyze

# Check build output
ls -lh dist/
```

## License

MIT
