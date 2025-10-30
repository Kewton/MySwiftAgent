# myAgentDesk

**AI Agent Desktop Interface** - An OpenWebUI-inspired interface with Dify workflow elements.

## 🎨 Design Philosophy

- **OpenWebUI-inspired**: Modern chat interface, dark mode support, clean typography
- **Dify workflow elements**: Visual workflow builder, node-based agent orchestration
- **Built with**: SvelteKit, TypeScript, Tailwind CSS

## 🚀 Quick Start

### Prerequisites

- Node.js 20.x or later
- npm 10.x or later

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Open browser at http://localhost:5173
```

### Build

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

## 📦 Project Structure

```
myAgentDesk/
├── src/
│   ├── routes/              # SvelteKit pages
│   │   ├── +layout.svelte  # Root layout
│   │   ├── +page.svelte    # Home page
│   │   ├── agents/         # Agents page
│   │   └── settings/       # Settings page
│   ├── lib/                 # Shared libraries
│   │   ├── components/     # Reusable Svelte components
│   │   └── utils/          # Utility functions
│   ├── app.html            # HTML template
│   └── app.css             # Global styles (Tailwind)
├── static/                  # Static assets
├── tests/                   # Test files
└── package.json            # Project configuration
```

## 🛠️ Development Commands

| Command              | Description                          |
| -------------------- | ------------------------------------ |
| `npm run dev`        | Start development server (port 5173) |
| `npm run build`      | Build for production                 |
| `npm run preview`    | Preview production build (port 8000) |
| `npm test`           | Run unit tests (Vitest)              |
| `npm run test:e2e`   | Run E2E tests (Playwright)           |
| `npm run lint`       | Run ESLint                           |
| `npm run format`     | Format code with Prettier            |
| `npm run type-check` | TypeScript type checking             |

## 🎯 Features

### Phase 1: Project Foundation ✅ Complete

- ✅ SvelteKit + TypeScript project setup
- ✅ Tailwind CSS configuration (OpenWebUI + Dify color palette)
- ✅ Dark mode support (class-based, localStorage persistence)
- ✅ Responsive navigation

### Phase 2: Wireframe Implementation ✅ Complete

- ✅ Full wireframe implementation (3 pages)
  - **Home Page**: OpenWebUI-style chat interface with sidebar
  - **Agents Page**: Dify-style agent cards with search/filter
  - **Settings Page**: Configuration UI with Cloudflare API settings
- ✅ 5 reusable components (Button, Card, Sidebar, ChatBubble, AgentCard)
- ✅ OpenWebUI-style chat interface (user/assistant bubbles)
- ✅ Dify-style workflow nodes (gradient cards, status indicators)
- ✅ Agent management UI (6 demo agents, category filtering)

### Phase 3: Docker/CI/CD Integration ✅ Complete

- ✅ Dockerfile (Multi-stage build for production)
- ✅ Health check endpoint (`/health` API)
- ✅ CI/CD integration (multi-release.yml)
- ✅ Non-root user execution (sveltekit:1001)
- ✅ Environment variables documentation (.env.example)

### Phase 4: Testing & Quality ✅ Complete

- ✅ Unit tests (42 tests passing, Vitest)
- ✅ Test coverage: 13.71% overall, **71.59% components**
- ✅ ESLint: 0 errors
- ✅ TypeScript type checking: 0 errors
- ✅ Accessibility improvements (keyboard navigation, ARIA roles)

### Phase 5: Future Enhancements 🚀

- ⏳ Cloudflare Workers integration (proxy configured, UI ready)
- ⏳ Real AI agent connectivity
- ⏳ E2E tests (Playwright)
- ⏳ Authentication & user management

## 🌐 Tech Stack

- **Framework**: SvelteKit 2.x
- **Language**: TypeScript (strict mode)
- **Styling**: Tailwind CSS 3.x
- **Build Tool**: Vite 5.x
- **Testing**: Vitest + Playwright
- **Linting**: ESLint + Prettier
- **Deployment**: Docker (adapter-node)

## 📝 License

MIT

## 🤝 Contributing

This project follows the MySwiftAgent monorepo conventions. See [NEW_PROJECT_SETUP.md](../docs/procedures/NEW_PROJECT_SETUP.md) for details.

## 📚 Related Documentation

- [SvelteKit Documentation](https://kit.svelte.dev/docs)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [OpenWebUI Project](https://github.com/open-webui/open-webui)
- [Dify Project](https://github.com/langgenius/dify)
