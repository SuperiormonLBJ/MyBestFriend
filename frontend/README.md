# MyBestFriend Frontend

Interactive chatbot UI for the digital twin — ask anything about Beiji (career, projects, hobbies).

## Features

- **Chatbot** with text and voice input (Web Speech API)
- **Admin Panel** placeholder for knowledge base management
- **Dark / Light mode** with system preference detection
- **Sidebar navigation** — Chatbot + Admin Panel

## Stack

- Next.js 16 (App Router)
- Tailwind CSS v4
- Lucide React icons
- AI-Native UI design system (Caveat + Quicksand, indigo palette)

## Setup

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Backend

The chatbot calls the backend API at `http://127.0.0.1:8000` by default. To run the backend:

```bash
cd ../backend
uv run uvicorn src.api_server:app --reload --host 0.0.0.0 --port 8000
```

Set `BACKEND_URL` (or `NEXT_PUBLIC_BACKEND_URL`) in `.env.local` to override the backend URL.

## Voice Input

Voice input uses the browser’s Web Speech API. It works in Chrome, Edge, and Safari. A fallback message is shown if the API is unavailable.
