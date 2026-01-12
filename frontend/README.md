# Frontend - PineOS Referral System

React TypeScript frontend for the PineOS referral system.

## Setup

1. Install dependencies:
```bash
npm install
```

2. Run the development server:
```bash
npm run dev
```

The app will be available at `http://localhost:5173`

## Build

To create a production build:
```bash
npm run build
```

## Project Structure

```
frontend/
├── src/
│   ├── App.tsx         # Main application component
│   ├── App.css         # App styles
│   ├── main.tsx        # Application entry point
│   └── index.css       # Global styles
├── index.html          # HTML template
├── package.json        # Dependencies
├── tsconfig.json       # TypeScript config
├── vite.config.ts      # Vite configuration
└── README.md           # This file
```

## Tech Stack

- **React 18**: UI library
- **TypeScript**: Type safety
- **Vite**: Build tool and dev server
- **React Router**: Navigation (to be implemented)
- **Axios**: HTTP client (to be implemented)

## Development

The frontend is configured to proxy API requests to the backend at `http://localhost:8000`.
