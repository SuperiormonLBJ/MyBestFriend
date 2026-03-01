---
type: project
title: DevOps Automation Portal
importance: high
year: 2024
tags: [software-engineering, full-stack, database, springboot, devops, uob, automation]
---

## 1. Overview

**Domain:** DevOps Automation / Internal Platform

**Role:** Full-stack AI/Software Engineer

**Duration:** Aug 2023 – Present

**Summary:**

Centralized DevOps automation portal integrating CI/CD, RBAC, and service scaffolding.

## 2. Problem (Pain)

- No unified DevOps interface
- Manual CI/CD setup
- Fragmented permission control
- Inefficient onboarding workflows

## 3. Solution (Architecture)

**High-level Design**

- Frontend: Angular dashboard
- Backend: Spring Boot REST APIs
- Auth: Keycloak (OIDC + JWT)
- Integration: Jenkins, Bitbucket, Jira
- DB: MSSQL

**Core Modules**

- Permission automation
- Pipeline generation
- Microservice scaffolding
- Image onboarding

## 4. Tech Stack

**Backend**

- Java, Spring Boot
- REST API
- MSSQL

**Frontend**

- Angular
- Lazy loading modules

**DevOps**

- Jenkins
- Docker
- Bitbucket

**Security**

- Keycloak
- OAuth2 / OIDC
- RBAC

## 5. AI / Automation Elements (Important for AI roles)

- Workflow automation
- Template generation
- Internal developer productivity tooling

## 6. Challenges

### 6.1 Long-running DevOps Operations

**Problem**

- Jenkins job creation and pipeline bootstrap took 20–60s.
- Synchronous REST caused UI timeout and poor UX.

**Solution**

- Introduced async job orchestration pattern:
    - Job request stored in DB
    - Background worker triggers Jenkins
    - Status polling API for frontend

**Tech Options Considered**

- Kafka
- Redis Queue
- DB polling (chosen initially for simplicity)

**Tradeoffs**

- DB polling simpler but less scalable.
- Kafka planned for future scale.

**Impact**

- Eliminated UI timeout issues
- Improved portal responsiveness

### 6.2 Metadata Drift (Portal vs Manual Changes)

**Problem**

- Developers sometimes modified Jenkins pipelines directly.
- Portal state became inconsistent.

**Solution**

- Introduced:
    - Scheduled reconciliation job
    - Metadata validation rules
    - Portal ownership enforcement

**Tradeoffs**

- Hard enforcement vs flexible override

**Future Direction**

- Event-driven sync via Jenkins webhook

## 7. Engineering Decisions (High RAG Value)

- Async job queue instead of synchronous APIs
- JWT-based stateless authentication
- Modular Angular architecture

## 8. Performance Optimization

- Lazy loading modules
- Server-side pagination
- Virtual scrolling
- OnPush change detection

## 9. Security Design

- OIDC login flow via Keycloak
- JWT bearer token
- @PreAuthorize RBAC enforcement

## 10. Results (Metrics)

- 50+ teams onboarded
- 100+ daily developers
- Reduced CI/CD onboarding time

## 11. Future Improvements

- Introduce async job queue (Kafka / Redis)
- Improve metadata sync
- Add caching layer