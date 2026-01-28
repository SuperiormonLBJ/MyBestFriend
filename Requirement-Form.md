⚡ RAG Chatbot Requirement Form

1. Goal
	•	One-line purpose:
        “An AI chatbot that lets HR quickly understand my technical depth and working style without reading my resume.”
	•	Success looks like:
        - HR understands my profile in <1 minutes
        - Shows my AI/RAG engineering skills
        - Answer with objective fact with no guessing
        - Demonstrate on my personal life and attitude
	•	Failure looks like:
        - Gives generic answers like ChatGPT, not grounded in my actual work.

2. Users
	•	Primary user: HR, Hiring Manager, Recruiter, Interviewer,Me
	•	AI level: Tech
	•	Top 3 questions they’ll ask:
        1.	How is Beiji's skill set on RAG?
        2.	What is Beiji's educational background?
        3.	What is Beiji's hobby and lifestyle?


3. Bot Persona
	•	Represents me as: Engineer with backend, AI and DevOps experience
	•	Tone: Friendly and Technical
	•	Never say: anything rude or impolite

4. Knowledge Scope
	•	Docs ingested: CV, LinkedIn Page, Personal Web Page
	•	Allowed knowledge:
        - Tech skills
        - Career 
        - Learning 
        - Side projects 
        - Personal interests

5. Question Rules
	•	Out-of-scope questions: Refuse
	•	Conflicts in docs: Redirect to my email as a query separately


6. RAG Behavior
	•	Ground answers in docs: Always
	•	Citations: Yes
	•	Detail level: High-level

7. Safety
	•	Hard red lines: consider this part later in the design, but leave a spot for this 
	•	Soft red lines: consider this part later in the design, but leave a spot for this 

8. Quality Bar
	•	Good answers must:
        - Reference projects 
        - Explain why

9. Tech Constraints 
	•	LLM: OpenAI
	•	Vector DB: use Chroma first to try then switch to Pinecone for consistency
    •	RAG evaluation: RAGAS
    •	Embedding Model: text-embedding-3-large
	•	AI framework: OpenAI SDK
    •	Tools: 
        - Notify_Unknown_Question (Notify me on email for the hard questions)
    •	Non-functional requirement: 
        - low latency
        - Easy for future feature addon or tech-stack migration

10. Output Required from AI Planner
    - Architecture
    - Ingestion pipeline
    - Chunking strategy
    - Eval plan
    - Build roadmap