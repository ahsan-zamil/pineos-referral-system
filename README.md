# PineOS Referral System

A full-stack referral system built for the PineOS challenge.

## Project Structure

```
pineos-referral-system/
├── backend/          # FastAPI backend application
├── frontend/         # React TypeScript frontend application
└── README.md         # Project documentation
```

## Tech Stack

### Backend
- **FastAPI**: Modern, fast web framework for building APIs
- **Python 3.8+**: Programming language

### Frontend
- **React**: UI library
- **TypeScript**: Type-safe JavaScript
- **Vite**: Build tool and dev server

## Getting Started

### Backend Setup

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

The backend API will be available at `http://localhost:8000`

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:5173`

## Features

- User referral system
- Referral tracking
- Analytics dashboard
- User management

## Development

This project is part of the PineOS referral system challenge.

## License

MIT
