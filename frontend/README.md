# ElasticSeer Chat UI

A custom frontend that replicates the Kibana Agent Builder chat interface, connecting directly to the ElasticSeer orchestrator agent.

## Features

- 🎨 **Kibana-style UI** - Matches Elastic's design system (colors, fonts, layout)
- 💬 **Real-time chat** - Direct connection to ElasticSeer agent via Kibana API
- 📝 **Conversation history** - Multiple conversations saved in localStorage
- 🤖 **Autonomous actions** - Create PRs, analyze incidents, search code from chat
- ✨ **Markdown rendering** - Rich formatting for agent responses
- 🔄 **Loading states** - Visual feedback while agent is thinking

## Quick Start

### Install Dependencies

```bash
npm install
```

### Start Development Server

```bash
npm run dev
```

The app will be available at http://localhost:5173

### Build for Production

```bash
npm run build
```

## Architecture

```
Frontend (React + Vite)
    ↓
FastAPI Backend (localhost:8001)
    ↓
Kibana Agent Builder API
    ↓
ElasticSeer Orchestrator Agent
```

## Configuration

The frontend connects to the backend via Vite's proxy configuration in `vite.config.ts`:

```typescript
proxy: {
  '/api': {
    target: 'http://localhost:8001',
    changeOrigin: true,
  },
}
```

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Styling (Elastic theme)
- **Lucide React** - Icons
- **React Markdown** - Markdown rendering
- **Axios** - HTTP client

## Project Structure

```
frontend/
├── src/
│   ├── pages/
│   │   └── AgentChat.tsx      # Main chat interface
│   ├── App.tsx                # App router
│   ├── main.tsx               # Entry point
│   └── index.css              # Global styles (Elastic theme)
├── public/                    # Static assets
├── package.json               # Dependencies
├── vite.config.ts             # Vite configuration
├── tailwind.config.js         # Tailwind configuration
└── tsconfig.json              # TypeScript configuration
```

## Usage

### Starting a Conversation

1. Click "New conversation" in the sidebar
2. Type your message in the input box
3. Press Enter or click the send button

### Example Prompts

```
Show me recent incidents
```

```
What are the current anomalies in the api-gateway service?
```

```
Search for authentication code in the repository
```

```
Create a PR for INC-002
```

### Keyboard Shortcuts

- **Enter** - Send message
- **Shift + Enter** - New line in message

## Customization

### Changing Colors

Edit `tailwind.config.js` to customize the Elastic theme:

```javascript
colors: {
  elastic: {
    blue: '#0077CC',
    darkBlue: '#006BB4',
    // ... more colors
  }
}
```

### Changing Agent ID

Edit `backend/app/api/agent_chat.py`:

```python
agent_id = "your-agent-id"
```

### Changing Backend URL

Edit `vite.config.ts`:

```typescript
proxy: {
  '/api': {
    target: 'http://your-backend-url',
    changeOrigin: true,
  },
}
```

## Development

### Hot Reload

The dev server supports hot module replacement (HMR). Changes to React components will be reflected immediately without a full page reload.

### Type Checking

```bash
npm run build
```

This runs TypeScript type checking before building.

### Linting

```bash
npm run lint
```

## Troubleshooting

### Frontend can't reach backend

1. Check backend is running: `curl http://localhost:8001/health`
2. Check Vite proxy configuration in `vite.config.ts`
3. Check browser console for CORS errors

### Conversation history not saving

1. Check browser localStorage is enabled
2. Clear localStorage: `localStorage.clear()` in browser console
3. Check browser console for errors

### Styles not loading

1. Check Tailwind is installed: `npm list tailwindcss`
2. Rebuild: `npm run build`
3. Clear browser cache

## License

MIT
