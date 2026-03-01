---
type: project
title: Portfolio Webpage
importance: high
year: 2025
tags: [nextjs, react, typescript, tailwindcss, portfolio, blog, personal-brand, vercel]
---

## **1. Overview**

**What is the project about?**

A modern, single-page personal portfolio and blog built with Next.js 14 and Tailwind CSS.

It showcases featured engineering/AI projects and personal hobbies, with a cinematic hero, “About Me” overlay, background music, and contact section to support personal branding and discovery.

## **2. Problem / Pain Points**

- Hard to present projects, AI experiments, and background in a cohesive, visually engaging way.
- GitHub alone doesn’t communicate story, personality, or cross-domain interests (AI, backend, hobbies).
- No central place to direct recruiters / collaborators with curated links, visuals, and contact info.

## **3. Actions Taken / Solution**

- Designed and implemented a **Next.js 14 App Router** site with a modern, animated hero and “About Me” experience.
- Created a **typed post model** (Post, FeaturedPost, HobbyPost) plus curated **data modules** for featured tech projects and non-tech hobbies.
- Implemented **featured projects grid** with images, tags (tech logos), and external links to GitHub/YouTube/demo pages.
- Added **hobby section (“Passion Beyond Tech”)** with background images and overlays to humanize the profile.
- Built an always-available **contact section** (phone, email, WhatsApp, LinkedIn) for easy outreach.
- Added **background music control** in RootLayout with autoplay handling and a floating control button.

## **4. Technical Architecture**

**Frontend**

- **Next.js 14 (App Router) + React 18 + TypeScript** for a modern, type-safe SPA-like UX.
- **Tailwind CSS** (with tailwind.config.js and postcss.config.js) for utility-first, highly customized styling.
- **Client components** for interactive sections:
- page.tsx handles hero animation, About Me toggle, featured posts, hobbies, and contact layout.
- layout.tsx manages background audio, fixed header, and global shell.
- **Responsive layout** using CSS grids and flexbox for cards and sections.

**Backend**

- No custom backend in this repo; it’s a static/SSR Next.js app.
- Data (projects, hobbies) is currently **in-code JSON-like arrays** under src/data, not fetched from an API.

**Integration & Persistence**

- **External links** used as integrations:
- GitHub repositories for detailed project code.
- YouTube for AI agent demo.
- External Prompt Library app link (Bitbucket-based prompt platform) and other projects.
- No database; persistence is purely via static data structures in the codebase.

**Developer Workflow**

- Standard Next.js scripts in package.json: dev, build, start, lint.
- Type-safe posts via src/types/post.ts to ensure consistency across featuredPosts and HobbyPosts.
- Simple local dev: npm run dev and open http://localhost:3000.

**Trade-offs**

- **Static data files** (featured-posts.ts, hobby-posts.ts) are simple and fast but require code changes for content updates; no CMS.
- **Single-page focus** (everything on /) simplifies navigation but may limit deep linking to individual posts.
- **Autoplay background music** enhances atmosphere but can be blocked by browsers and may not fit all user preferences.

## **5. Challenges & How They Were Overcome**

- **Balancing personality with professionalism:**

Solved with a cinematic hero and About Me overlay, plus clearly separated sections for projects vs hobbies.

- **Showcasing diverse projects (backend, AI, automation) coherently:**

Solved with typed FeaturedPost cards that unify titles, dates, tags, categories, and imagery.

- **Ensuring good UX with fixed header and media:**

Used a fixed header with backdrop blur, main content padding, and a floating music control button.

## **6. Business / Career Impact**

- **Stronger personal brand:** Central place to showcase AI agents, prompt library, banking systems, and other work.
- **Better recruiter and collaborator experience:** One link reveals skills, stack, and personality, with direct contact info.
- **Portfolio leverage:** Highlights experience in AI tooling (LLM-based reviewer, prompt library), backend banking systems, and automation.
- **Signals of craft:** Thoughtful UI animations, responsiveness, and attention to detail (music, video, social links).

## **7. Future Improvements**

- Turn static featuredPosts into **dynamic content** from a headless CMS or markdown posts.
- Add **individual project/blog detail pages** with more narrative, diagrams, and code snippets.
- Implement **tags/filters** on the featured projects grid (e.g., AI, Backend, Full-Stack).
- Enhance **SEO and analytics** (Open Graph tags, structured data, tracking).
- Add **hobby detail pages** with photos, stories, and stats (e.g., lifting PRs, dive logs, trips).

## **8. Dependencies**

- **Next.js 14.1.0** → framework, routing, app structure.
- **React 18.2.0 / React DOM** → UI rendering.
- **TypeScript 5.3.3** → static typing and safer refactors.
- **Tailwind CSS 3.4.1 + PostCSS + Autoprefixer** → styling pipeline.
- **React Icons** (present in package.json though not yet used in the main page) → iconography.
- **ESLint + eslint-config-next** → linting and basic code quality.

## **9. Signals for RAG / Career Retrieval**

- Modern frontend stack: **Next.js 14, React 18, TypeScript, Tailwind CSS**.
- Experience with **portfolio-quality UI/UX**, animations, and media (video background, music control).
- Demonstrated projects in **AI tooling, prompt infrastructure, banking systems**, and workflow automation (via linked repos).
- Personal branding and communication skills: clear About Me, social links, and multi-language identity.