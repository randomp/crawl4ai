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

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Frontend will be available at: http://localhost:5173
```

## Configuration

Edit `.env` file:

```env
VITE_API_BASE_URL=http://localhost:11235
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

## License

MIT
