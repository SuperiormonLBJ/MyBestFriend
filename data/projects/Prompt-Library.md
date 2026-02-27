---
type: project
title: Prompt Template Library
importance: high
year: 2025
tags: [springboot, react, postgres, keycloak, prompt-engineering, bitbucket, LLM]
---

## 1. Overview

**What is the project about?**  
Centralized prompt template library to standardize, version, and govern prompts across teams.  
Allows teams to create, approve, and maintain high-quality templates integrated with Bitbucket and Jira workflows.

## 2. Problem / Pain Points

- Different teams required different templates → duplication and inconsistency  
- Templates were scattered and lacked centralized management → low quality control  
- No lifecycle or access control for prompt templates → compliance risk

## 3. Actions Taken / Solution

- Designed and implemented **dashboard platform** connected with **Bitbucket**.  
- Workflow:
  1. User submits a template change request in platform
  2. System generates PR and adds request to approver queue
  3. Upon approval, dashboard reflects updated template + full change history  
- Added **access control / RBAC** to ensure governance  
- Integrated **Postgres** for metadata, PR info, chat memory  
- Cache for PR analysis / file diff  
- RAG embedding to detect duplicates (>0.9 similarity)  
- Guardrails: banned term search + LLM checks without API key or bank-sensitive data

## 4. Technical Architecture

### Frontend
- React 18 + TypeScript: predictable component model, safe refactors  
- MUI v5: fast, accessible UI  
- React Router v6: SPA routing  
- Jest + Testing Library: unit + UI tests  

### Backend
- Spring Boot 2.7 (Java 17): mature, stable ecosystem, Jackson JSON support  
- RestTemplate (non-reactive HTTP calls to Bitbucket)  
- dotenv-java for credential management  
- CORS config for local dev  

### Integration & Persistence
- Bitbucket: source-of-truth, stores template JSON files  
- Postgres: store template requests, metadata, chat memory  
- Jira: ticketing and approval logs  
- RAG: deduplication of templates  

### Developer Workflow
- Single-command dev start (`start-all`) for SPA + API  
- Shared TS interfaces for JSON contract safety  

### Trade-offs
- RestTemplate: simple but blocking → migrate to WebClient if upgrading  
- Bitbucket as storage: easy for audit, but limited offline / high-throughput capabilities  
- Webpack could be replaced with Vite for faster builds  

## 5. Challenges & How They Were Overcome

- **Template duplication:** RAG embeddings for similarity detection (>0.9 threshold)  
- **LLM Guardrails:** banned term search + no API key usage for sensitive data  
- **Approval compliance:** PR-based maker-checker workflow  

## 6. Business Impact

- **Centralized knowledge management:** eliminates duplication, enforces standards, version control  
- **Operational efficiency:** faster development, fewer errors, knowledge retention  
- **Compliance & Governance:** PR approvals, audit trail, department ownership  
- **Cross-team dependency:** AI/ML, Product, Customer Support, Compliance teams  
- **Metrics:** 20+ teams using platform, cycle time reduced 40%, adoption + satisfaction high  

## 7. Future Improvements

- Prompt analysis and metrics display (benchmarked on 100+ queries, string matching + LLM as judge)  
- Integration with AI training pipelines  
- Real-time collaboration / commenting  
- Mobile access  

## 8. Dependencies

- Bitbucket → template storage, PR workflow  
- Jira → ticket management / audit logs  
- Postgres → metadata, request tracking  
- Cache → PR analysis and file diff  
- RAG → duplicate detection  
- Guardrails → LLM safety checks  

## 9. Signals for RAG / Career Retrieval

- AI Platform / Prompt Infrastructure  
- Full lifecycle management + governance  
- Cross-team collaboration / operational efficiency  
- Compliance & maker-checker workflow  
- Tech stack signals: React, Spring Boot, Postgres, Bitbucket, RAG, LLM