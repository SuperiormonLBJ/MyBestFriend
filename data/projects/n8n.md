---
type: project
title: Agentic Workflow Automation Platform (n8n)
importance: high
year: 2025
tags: [automation, ai-workflow, agentic-ai, low-code-platform, platform-engineering, uob]
---
## 1. Overview

**Domain:** Workflow Automation / AI Automation Platform

**Role:** Platform / AI Automation Engineer (Project Lead)

**Duration:** 2025 – Present

**Summary**

Designed and promoted an internal **agentic workflow automation platform** using n8n across United Overseas Bank by packaging n8n as a secure internal service.

The platform enables teams to build automation and AI workflows using visual pipelines, integrations, and custom nodes without heavy engineering overhead.

## 2. Problem (Pain)

- Organization lacked **agentic workflow capabilities**
- Many teams had repetitive manual processes
- Non-technical teams struggled to build automation pipelines
- Integration across tools required heavy scripting effort

Typical examples:

- Manual ticket handling
- Repetitive deployment orchestration
- Cross-tool notification workflows

## 3. Solution (Architecture)

**High-level Design**

- Packaged n8n as an **internal SaaS platform**
- Containerized deployment with secure access controls
- RBAC integrated with enterprise authentication
- Standardized workflow templates for teams

**Core Capabilities**

- Visual workflow orchestration
- AI workflow chains (RAG-ready pipelines)
- MCP-based agent orchestration support
- Custom node extensions (HTTP / code execution)

**Tool Integrations**

- Jira
- Confluence
- Jenkins
- JFrog Artifactory
- Microsoft Teams
- Microsoft Outlook

## 4. Tech Stack

**Platform**

- n8n
- Docker
- Internal cloud infrastructure

**Automation**

- Workflow orchestration
- REST integrations
- Custom nodes (HTTP / code execution)

**AI Enablement**

- Chain-based workflows
- RAG-ready architecture
- MCP-compatible agent patterns

## 5. AI / Automation Elements (High AI Signal)

- Agentic workflow orchestration
- Tool-based reasoning pipelines
- Template-driven automation
- Internal AI enablement platform

This project bridges:

- DevOps automation
- AI workflow orchestration
- Internal developer platform (IDP)

## 6. Key Engineering Challenges & Solutions

### **6.1 Adoption Barrier Across Teams**

**Problem**

- Teams lacked automation knowledge.
- Workflow setup required scripting experience.

**Solution**

- Introduced standardized templates
- Conducted internal enablement sessions
- Built reusable workflow patterns

**Impact**

- Lowered automation entry barrier significantly

### 6.2 Enterprise Security & RBAC

**Problem**

- n8n default setup not enterprise-ready.

**Solution**

- Added RBAC controls
- Integrated internal authentication
- Enforced environment isolation

### 6.3 Multi-tool Integration Complexity

**Problem**

- Different authentication models across tools.

**Solution**

- Centralized credential management
- Standardized integration patterns

## 7. Engineering Decisions (High RAG Value)

- Packaged n8n as internal SaaS instead of ad-hoc deployments
- Template-driven workflow standardization
- Custom node extensibility for edge cases

## 8. Architecture Patterns Used

- Internal Developer Platform (IDP)
- Agentic workflow orchestration
- Template-driven automation
- Tool-integration orchestration layer

## 9. Results (Impact)

- Adopted by multiple engineering teams
- Enabled both AI and non-AI automation use cases
- Strong internal feedback on productivity improvement
- Reduced manual workflow effort across teams
- Onboarded 10+ teams, generating 10k SGD savings per month from reduced man-hours

*(Add metrics later if available: workflow count, automation hours saved, team adoption rate)*

## 10. Future Improvements

- Event-driven workflow triggers (Kafka)
- Centralized workflow observability
- LLM-native workflow templates
- Deeper RAG integration for internal knowledge automation