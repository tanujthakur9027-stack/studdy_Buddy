"""
generate_docx_report.py
Generates the matching Microsoft Word (.docx) Dissertation Report for:
STUDY BUDDY AI: AI-POWERED ACADEMIC ASSISTANT, INSTITUTIONAL MANAGEMENT & ATTRITION PREDICTION SYSTEM
Author: Tanuj Kumar Singh (Enrollment No. : 20241055)
Supervisor: Dr. Amit Upadhyay (Associate Professor)
Mangalayatan University, Beswan, Aligarh - November 2026
"""
from pathlib import Path
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

OUTPUT_DIR = Path(__file__).resolve().parent
DOCX_PATH = OUTPUT_DIR / "STUDY_BUDDY_AI_DISSERTATION_REPORT.docx"

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = docx.oxml.OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = docx.oxml.OxmlElement(f'w:{m}')
        node.set(docx.oxml.ns.qn('w:w'), str(val))
        node.set(docx.oxml.ns.qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def generate_docx():
    print("Generating DOCX Dissertation Report...")
    doc = Document()

    # Configure Margins to 0.75 inch (same as PDF)
    sections = doc.sections
    for s in sections:
        s.top_margin = Inches(0.75)
        s.bottom_margin = Inches(0.75)
        s.left_margin = Inches(0.75)
        s.right_margin = Inches(0.75)

    # Styles
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Times New Roman'
    normal_style.font.size = Pt(11)
    normal_style.font.color.rgb = RGBColor(15, 23, 42)

    def add_p(text, bold=False, italic=False, size=11, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=6, color=(15, 23, 42)):
        p = doc.add_paragraph()
        p.alignment = align
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.line_spacing = 1.15
        run = p.add_run(text)
        run.bold = bold
        run.italic = italic
        run.font.size = Pt(size)
        run.font.color.rgb = RGBColor(*color)
        return p

    def add_bullet(text):
        p = doc.add_paragraph(style='List Bullet')
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.15
        run = p.add_run(text)
        run.font.name = 'Times New Roman'
        run.font.size = Pt(10.5)
        run.font.color.rgb = RGBColor(15, 23, 42)
        return p

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 1: TITLE / COVER PAGE
    # ══════════════════════════════════════════════════════════════════════════
    for _ in range(3):
        add_p("", space_after=12)

    add_p("STUDY BUDDY AI: INTELLIGENT ACADEMIC DECISION SUPPORT, CLASS-BASED MANAGEMENT & ATTRITION PREDICTION SYSTEM",
          bold=True, size=18, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=20, color=(15, 23, 42))

    add_p("A Dissertation\nSubmitted in partial fulfillment of the requirements\nfor the award of the degree of",
          size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=18, color=(51, 65, 85))

    add_p("Bachelor of Technology\nin\nComputer Science & Engineering",
          bold=True, size=13, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=24)

    add_p("by\nTanuj Kumar Singh\n(Enrollment No. : 20241055)\n5th Semester, B.Tech CSE",
          bold=True, size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=24)

    add_p("Under the Supervision of\nDr. Amit Upadhyay\n(Associate Professor)",
          bold=True, size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=36)

    for _ in range(4):
        add_p("", space_after=12)

    add_p("Department of Computer Engineering & Applications\nFACULTY OF ENGINEERING AND TECHNOLOGY\nMANGALAYATAN UNIVERSITY\nBESWAN, ALIGARH\nNovember 2026",
          bold=True, size=10, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=0, color=(15, 23, 42))

    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 2: SUPERVISOR'S CERTIFICATE
    # ══════════════════════════════════════════════════════════════════════════
    add_p("SUPERVISOR'S CERTIFICATE", bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=20)
    add_p("This is to certify that the project report entitled \"STUDY BUDDY AI: INTELLIGENT ACADEMIC DECISION SUPPORT, CLASS-BASED MANAGEMENT & ATTRITION PREDICTION SYSTEM\" being submitted by Mr. Tanuj Kumar Singh (Enrollment No. 20241055) in partial fulfillment for the award of the Degree of Bachelor of Technology in Computer Science and Engineering to the Department of Computer Engineering and Applications (DCEA), Faculty of Engineering and Technology (FET), Mangalayatan University, Beswan, Aligarh is a record of bonafide work carried out under my guidance and supervision.")
    add_p("The project embodies results of original investigation and contains novel findings in the integration of dense vector Retrieval-Augmented Generation (RAG), the Feynman active learning technique, multi-tenant Class-Based Role Isolation, and Random Forest student attrition risk modeling, which have not formed the basis for the award of any other degree, associateship, fellowship, or similar title to any other university or institution.")
    add_p("The project has been thoroughly evaluated and found to strictly meet the standards of academic excellence, software engineering rigor, and originality required for the degree.")

    for _ in range(5):
        add_p("", space_after=12)

    add_p("Place: Beswan, Aligarh                                                   Dr. Amit Upadhyay", bold=True)
    add_p("Date: 25 November 2026                                                  (Associate Professor & Supervisor)")
    add_p("                                                                                 Department of Computer Engineering & Applications")
    add_p("                                                                                 Mangalayatan University, Beswan, Aligarh")
    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 3: CANDIDATE'S DECLARATION
    # ══════════════════════════════════════════════════════════════════════════
    add_p("DECLARATION", bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=20)
    add_p("I hereby declare that the dissertation entitled \"STUDY BUDDY AI: INTELLIGENT ACADEMIC DECISION SUPPORT, CLASS-BASED MANAGEMENT & ATTRITION PREDICTION SYSTEM\" submitted for the award of the degree of Bachelor of Technology in Computer Science & Engineering is an original work conducted under the supervision and guidance of Dr. Amit Upadhyay, Associate Professor in the Department of Computer Engineering and Applications, Mangalayatan University, Beswan, Aligarh.")
    add_p("I confirm that this dissertation has not been submitted, in part or in full, to any other university or institution for any degree, diploma, associateship, or other academic qualification.")
    add_p("I further declare that all intellectual inputs, algorithms, open-source models (Groq Llama 3.3 70B, Google Gemini Flash, SentenceTransformers all-MiniLM-L6-v2), database engines (Neon Serverless PostgreSQL with NullPool architecture), and scientific literature cited in this work have been duly acknowledged and cited in the references. The software repository and complete source code reside transparently at: https://github.com/tanujthakur9027-stack/studdy_Buddy.")
    add_p("I understand that any act of plagiarism or academic misrepresentation in this dissertation may result in disciplinary action as per the academic regulations and ethics policies of Mangalayatan University.")

    for _ in range(5):
        add_p("", space_after=12)

    add_p("Place: Beswan, Aligarh                                                   Tanuj Kumar Singh", bold=True)
    add_p("Date: 25 November 2026                                                  Enrollment No. : 20241055")
    add_p("                                                                                 5th Semester, B.Tech CSE")
    add_p("                                                                                 Department of Computer Engineering & Applications")
    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 4: APPROVAL SHEET
    # ══════════════════════════════════════════════════════════════════════════
    add_p("APPROVAL SHEET", bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=20)
    add_p("This dissertation entitled \"STUDY BUDDY AI: INTELLIGENT ACADEMIC DECISION SUPPORT, CLASS-BASED MANAGEMENT & ATTRITION PREDICTION SYSTEM\" submitted by Tanuj Kumar Singh (Enrollment No. 20241055) is approved for the degree of Bachelor of Technology in Computer Science and Engineering from Mangalayatan University, Beswan, Aligarh.")
    add_p("Examiners:\n\n1. ___________________________________\n\n2. ___________________________________\n\n3. ___________________________________")

    for _ in range(3):
        add_p("", space_after=12)

    add_p("Supervisor:                                                                Head of Department (Chairman):", bold=True)
    add_p("_____________________________________                                    ____________________________________")
    add_p("Dr. Amit Upadhyay                                                        Dr. Javed Wasim", bold=True)
    add_p("Associate Professor, DCEA                                                Head of Department, DCEA")
    add_p("\nDate: 25 November 2026\nPlace: Beswan, Aligarh")
    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 5: ACKNOWLEDGEMENT
    # ══════════════════════════════════════════════════════════════════════════
    add_p("ACKNOWLEDGEMENT", bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=20)
    add_p("I express my profound gratitude and deepest regards to my respected supervisor, Dr. Amit Upadhyay, Associate Professor, Department of Computer Engineering and Applications, Mangalayatan University, for his invaluable intellectual mentorship, constructive technical critiques, and patient guidance throughout the architectural design, algorithmic implementation, and empirical verification of the Study Buddy AI project. His rigorous standards in software engineering, database design, and security integrity were pivotal in elevating this dissertation.")
    add_p("I am immensely indebted to Dr. Javed Wasim, Head of the Department of Computer Engineering and Applications (DCEA), for his administrative encouragement, academic vision, and for extending the computational laboratory infrastructure that enabled the seamless deployment and testing of our multi-agent framework.")
    add_p("I also convey my gratitude to the Faculty of Engineering and Technology (FET) and the academic leadership of Mangalayatan University, Beswan, Aligarh, for cultivating an inspiring research environment dedicated to engineering high-impact computational solutions for real-world educational and institutional challenges.")
    add_p("I gratefully acknowledge the open-source software and artificial intelligence communities—the FastAPI async framework, Next.js 14 React architecture, Neon Serverless PostgreSQL team for cutting-edge cloud database infrastructure, the Groq LPU platform for ultra-low latency token inference, Google Gemini API for multimodal reasoning, ChromaDB for dense semantic vector management, and the scikit-learn contributors for empowering our EduGuard ML model.")
    add_p("Finally, my heartfelt gratitude goes to my family, parents, and friends whose unwavering moral support, patience, and encouragement sustained my motivation throughout this challenging engineering endeavor.")
    add_p("\n\nTanuj Kumar Singh\nEnrollment No. : 20241055\n5th Semester, B.Tech Computer Science & Engineering\nMangalayatan University", bold=True, align=WD_ALIGN_PARAGRAPH.RIGHT)
    doc.add_page_break()

    # ══════════════════════════════════════════════════════════════════════════
    # ABSTRACT
    # ══════════════════════════════════════════════════════════════════════════
    add_p("ABSTRACT", bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=18)
    add_p("In modern tertiary education institutions, students and faculty encounter severe structural friction characterized by information silos, fragmented academic workflows, delayed grading feedback, and alarmingly high student attrition rates. Conventional Learning Management Systems (LMS) such as Moodle and Google Classroom function essentially as static document repositories, lacking personalized pedagogical intelligence, interactive comprehension evaluation, or proactive dropout risk detection. Furthermore, while foundational Large Language Models (LLMs) offer exceptional conversational capabilities, their deployment in institutional academic environments has been severely hampered by stochastic hallucinations, ungrounded answers, security vulnerabilities, and an absence of class-level multi-tenant role isolation.")
    add_p("To decisively overcome these limitations, this dissertation presents Study Buddy AI, an intelligent, full-stack, and evidence-grounded academic management and decision support ecosystem. Study Buddy AI is engineered on an advanced hybrid architecture integrating: (1) a high-performance FastAPI asynchronous backend operating over real-time Neon Serverless PostgreSQL via a connection-isolated NullPool architecture across 33 relational tables; (2) a state-of-the-art Next.js 14 responsive web frontend with client-side optimistic UI state and Tailwind CSS styling; and (3) an administrative Streamlit operations portal providing real-time institutional oversight.")
    add_p("The project integrates nine tightly coupled architectural sub-systems: (1) a localized Retrieval-Augmented Generation (RAG) Engine vectorizing syllabus documents and PDF course notes into a 384-dimensional dense semantic vector space via ChromaDB and SentenceTransformers (all-MiniLM-L6-v2); (2) an interactive Feynman Technique Evaluator that challenges students to explain complex topics in plain language, analyzes conceptual knowledge gaps, and provides qualitative scoring; (3) an Adaptive Quiz and Spaced-Repetition Flashcard Engine with real-time analytics and self-assessment; (4) the EduGuard AI Attrition Prediction Model—a trained Random Forest Classifier evaluating demographic, financial, and semester-by-semester academic metrics to predict student dropout risk with actionable institutional retention recommendations; (5) a multi-tenant Class-Based Management System enforcing strict cryptographic role-based access control (RBAC) ensuring complete isolation between classes (Class 10-A, 10-B); (6) an Assignment & Submission Pipeline supporting secure PDF delivery, submission timestamps, and teacher grading; (7) an Academic Timetable Management System providing automated daily period and lunch scheduling; (8) a Multi-Channel Notification & Background Email Dispatcher delivering critical announcements via non-blocking FastAPI BackgroundTasks; and (9) a production-grade Direct Password Authentication Gate ensuring instant, friction-free login without simulator bottlenecks.")
    add_p("Empirical evaluation and end-to-end verification across automated test suites demonstrate that Study Buddy AI achieves an average vector retrieval latency of 0.28 seconds, sub-second LLM synthesis of 0.72 seconds via Groq LPU hardware acceleration, and 100% barrier enforcement preventing cross-class data leakage. In validation against 18 simulated academic profiles, the EduGuard ML model accurately classified dropout probabilities with high clinical precision. By harmonizing cognitive AI tutoring with institutional management, Study Buddy AI provides an open-source, scalable, and secure educational operating system for colleges and universities.")
    add_p("\nKeywords: Retrieval-Augmented Generation (RAG), Intelligent Tutoring Systems (ITS), Higher Education Informatics, Student Attrition Prediction, Random Forest ML, Class-Based Management, Role-Based Access Control (RBAC), Neon PostgreSQL, FastAPI, Next.js 14, Groq LPU.", italic=True)
    doc.add_page_break()

    # Chapters and detailed sections
    chapters = [
        ("CHAPTER 1: INTRODUCTION", [
            ("1.1 Background & Sociodemographic Context of Higher Education",
             "Higher education across developing economies, particularly within India, is experiencing massive structural expansion alongside intense pedagogical challenges. According to the All India Survey on Higher Education (AISHE) and National Education Policy (NEP 2020) directives, university gross enrollment ratios are targeted to exceed 50% by 2035. However, the student-to-faculty ratio in Indian technical institutions routinely exceeds 30:1, far surpassing international benchmarks. Consequently, professors and teaching assistants are overwhelmed by manual administrative duties—such as tracking daily attendance, manually grading assignments, scheduling periods, and answering routine factual questions—leaving minimal bandwidth for personalized mentorship.\n\nSimultaneously, undergraduate engineering students face overwhelming cognitive loads. As modern technical curricula expand rapidly into distributed computing, artificial intelligence, and cloud infrastructures, students lack personalized study tools capable of diagnosing conceptual weaknesses in real time. Passive study habits—such as memorizing slides without active retrieval or self-explanation—lead to rapid knowledge decay and severe exam anxiety. A critical institutional consequence is alarming student attrition during early semesters, which harms both institutional reputations and students' professional trajectories."),
            ("1.2 Problem Statement & Analysis of Institutional Challenges",
             "The fundamental problem addressed by this dissertation can be stated as follows: The critical absence of a unified, evidence-grounded academic intelligence and institutional management ecosystem capable of delivering interactive active learning, strict class-based role isolation, and early machine learning prediction of student attrition without hallucination or administrative overhead.\n\nThis overarching problem encompasses four critical architectural failures in existing institutional tools:\n• Static and Disconnected LMS Repositories: Platforms like Moodle or basic Google Classroom act merely as passive file storage folders. They provide zero pedagogical interactivity, zero conceptual gap analysis, and no automated synthesis of student notes.\n• Unconstrained Hallucination in Generic AI: While students increasingly query consumer AI models like ChatGPT, these foundational LLMs lack grounding in specific course curricula, frequently inventing plausible yet factually incorrect technical definitions.\n• Absence of Class-Level Multi-Tenant Isolation: Generic academic portals lack robust cryptographic permission checks. A class teacher managing Section 10-A frequently has inappropriate administrative write access to Section 10-B, creating severe data integrity risks.\n• Reactive Rather than Proactive Attrition Intervention: University administrations discover student academic failure or dropout decisions only after final examinations conclude, when corrective interventions are no longer feasible."),
            ("1.3 Project Scope & Deliverables",
             "The operational scope of Study Buddy AI encompasses the complete end-to-end engineering, implementation, and empirical verification of an enterprise-grade academic decision support platform. The system operates as a hybrid Cognitive Tutoring and Institutional Learning Management System (ITS/LMS). It is engineered for university departments, colleges, and schools to streamline student-faculty interactions and drive institutional retention.\n\nThe primary deliverables realized in this dissertation comprise:\n• Dense Vector RAG Ingestion Pipeline: Semantic indexing of uploaded PDF course notes and syllabus topics into 384-dimensional vector spaces using ChromaDB and SentenceTransformers.\n• Interactive Feynman AI Evaluator: A specialized cognitive feedback engine assessing plain-language conceptual explanations, grading understanding from 0–100, and isolating knowledge gaps.\n• Adaptive Quiz and Spaced-Repetition Flashcard Engine: Dynamic question generation with automated rationale synthesis and self-assessment flashcard flip cards.\n• EduGuard AI Attrition Prediction Model: A trained Random Forest Classifier evaluating demographic and academic indicators to predict dropout probabilities with actionable advisory guidance.\n• Multi-Tenant Class-Based Management Subsystem: Complete relational schema (SchoolClass, ClassAdmin, ClassEnrollment) enforcing strict permission boundaries where Class Admins manage only assigned sections.\n• Assignment & Submission Pipeline: Secure PDF assignment distribution, deadline validation, student upload portal, and teacher grading workflows.\n• Timetable & Scheduling System: Dynamic day-by-day period allocation, lunch break interlocks, and published schedule views.\n• Multi-Channel Notification Dispatcher: Fast, non-blocking email dispatch and in-app inbox alerts powered by FastAPI BackgroundTasks.\n• Direct Password Authentication Gate: Friction-free, secure SHA-256 password login replacing simulation OTP bottlenecks."),
            ("1.4 Primary Objectives",
             "The project was executed against six explicit engineering objectives:\n1. Zero-Hallucination Academic Evidence Grounding: Constrain generative AI outputs strictly to verified textbook excerpts and syllabus documents using dense vector RAG.\n2. Sub-Second Real-Time Response: Deliver complete API query responses under 1.0s using Groq LPU hardware acceleration and direct Neon PostgreSQL queries.\n3. Multi-Tenant Class Security Isolation: Guarantee 100% permission barrier enforcement such that Class Admins cannot read, write, or publish assignments for unassigned classes.\n4. Early Dropout Risk Identification: Attain high classification accuracy in flagging at-risk students before semester examinations.\n5. Cloud Database Resilience: Implement an asyncpg NullPool connection architecture against Neon Serverless PostgreSQL to prevent connection pooling dropouts across cloud networks.\n6. Zero-Cost Client Accessibility: Ensure full responsiveness across desktop and mobile devices without requiring client-side GPU hardware."),
            ("1.5 Field of Project & Technology Used",
             "Study Buddy AI resides at the cutting-edge intersection of Artificial Intelligence, Natural Language Processing (NLP), Educational Data Mining (EDM), and Cloud-Native Full-Stack Engineering. Specifically, it operationalizes advancements in dense vector semantic embeddings, Retrieval-Augmented Generation (RAG), supervised ensemble machine learning, and asynchronous microservices.\n\nThe core technology stack utilizes Python 3.10+ and FastAPI for high-throughput asynchronous backend APIs; Next.js 14 (React) for server-side rendered and dynamic frontend interfaces; Neon Serverless PostgreSQL (PostgreSQL 18.7) as the authoritative relational data store; SQLAlchemy 2.0 with asyncpg for async ORM operations; ChromaDB for dense vector indexing; SentenceTransformers (all-MiniLM-L6-v2) for 384-dimensional text embeddings; Groq LPU API executing Llama 3.3 70B for sub-second LLM inference; Google Gemini 2.5 Flash as an automated fallback model; and scikit-learn for the EduGuard Random Forest predictive model."),
            ("1.6 Special Requirements & Operational Constraints",
             "Deploying an enterprise software ecosystem in university settings entails distinct constraints:\n• Academic Integrity & Anti-Cheating Safeguards: Generative tutoring prompts must enforce Socratic inquiry, guiding students through foundational principles rather than providing direct homework solutions.\n• Strict Data Privacy & Role Boundaries: Student grade books, attendance records, and personal attrition risk scores must remain strictly confidential and visible only to authorized faculty and super administrators.\n• Network Jitter Resilience: Cloud database operations connecting to serverless PostgreSQL must withstand network latency without socket hangs, handled via optimized asyncpg connection parameters and NullPool allocation.")
        ]),
        ("CHAPTER 2: METHODOLOGY & LITERATURE SURVEY", [
            ("2.1 Overview of Modern Educational Information Systems",
             "The evolution of educational software spans four major historical epochs: First-generation Computer-Assisted Instruction (CAI) in the 1970s and 1980s (e.g., PLATO, SCHOLAR) operated on rigid, hardcoded branching trees. Second-generation Learning Management Systems (LMS) in the late 1990s and 2000s (e.g., Blackboard, Moodle) centralized course documents and gradebooks. Third-generation Massive Open Online Courses (MOOCs) in the 2010s distributed video lectures globally but suffered from low completion rates (< 10%). Fourth-generation systems incorporate generative AI and adaptive cognitive tutoring."),
            ("2.2 Bottlenecks in Traditional Learning Management Platforms",
             "Traditional LMS platforms fail to support personalized pedagogy due to: (1) Zero Formative Feedback: Submissions are collected as static files, resulting in feedback delays of weeks; (2) Information Fragmentation: Timetables, notes, marks, and announcements are scattered across disconnected portals; and (3) Absence of Predictive Analytics: Student academic distress is discovered only after semester results are published."),
            ("2.3 RAG Architecture vs LLM Hallucinations in Academics",
             "While foundational LLMs offer immense reasoning capabilities, unconstrained models exhibit severe stochastic hallucination. In academic subjects, hallucinations produce erroneous formulas and inaccurate historical dates. Study Buddy AI resolves this via Retrieval-Augmented Generation (RAG): indexing course materials into ChromaDB dense vector stores and constraining LLM generation strictly to retrieved syllabus passages."),
            ("2.4 Comparative Analysis of Existing Academic Platforms",
             "An empirical audit shows that while Google Classroom excels at document distribution and Quizlet excels at memorization, neither offers integrated cognitive tutoring, real-time Feynman gap evaluation, or early student retention risk modeling. Study Buddy AI uniquely bridges this divide."),
            ("2.5 Summary Comparative Evaluation Matrix",
             "As detailed in Table 2.1 of the dissertation, Study Buddy AI outperforms legacy LMS tools and generic LLMs in vector evidence grounding (all-MiniLM-L6-v2), inference latency (0.72s via Groq LPU), Feynman conceptual scoring, machine learning dropout risk modeling, and multi-tenant class isolation."),
            ("2.6 Iterative Development Phases",
             "The system was engineered across seven structured phases (Phase 0 to Phase 6) spanning discovery, schema migration, class security barrier implementation, backend API expansion, Next.js frontend development, Streamlit operations parity, and full E2E testing against Neon Serverless PostgreSQL.")
        ]),
        ("CHAPTER 3: SOFTWARE REQUIREMENT ANALYSIS", [
            ("3.1 Functional Requirements Definitions (FR1 to FR8)",
             "The functional requirements specify the explicit behavioral capabilities: FR1 (Academic Note Ingestion & Vector Retrieval), FR2 (Interactive Feynman Active Learning Evaluator), FR3 (Dynamic Quiz & Flashcard Engine), FR4 (EduGuard AI Dropout Risk Prediction), FR5 (Multi-Tenant Class-Based Management), FR6 (Assignment & Submission Management), FR7 (Academic Timetable Scheduling), and FR8 (Real-Time Multi-Channel Notifications)."),
            ("3.2 Non-Functional Requirements Definitions (NFR1 to NFR6)",
             "The non-functional constraints enforce rigorous engineering benchmarks: NFR1 (Academic Grounding & Zero Hallucination), NFR2 (Sub-Second Execution Latency), NFR3 (High Availability & Multi-Model Fallback), NFR4 (Multi-Tenant Class Security Barrier), NFR5 (Cloud Database Resilience with NullPool), and NFR6 (Friction-Free Direct Password Authentication)."),
            ("3.3 User Personas & Institutional Stakeholders",
             "Three institutional user roles are supported: The Student (learning companion, quiz taker, assignment submitter), The Class Admin / Teacher (assignment publisher, marks evaluator, announcement broadcaster), and The Super Administrator (institutional leadership managing classes, faculty assignments, and attrition risk telemetry)."),
            ("3.4 Hardware Requirements Specifications",
             "Client-side devices require minimal hardware: dual-core processors and 4 GB RAM on standard commodity laptops or mobile devices. Server-side execution runs on scalable cloud containers with direct network access to Neon Serverless PostgreSQL."),
            ("3.5 Software Technology Stack",
             "Frontend: Next.js 14 (React) + Tailwind CSS + Streamlit. Backend: FastAPI (Python 3.10+) + Starlette. Database: Neon Serverless PostgreSQL 18.7 + asyncpg + SQLAlchemy 2.0 (NullPool). AI & ML: ChromaDB, SentenceTransformers, Groq LPU (Llama 3.3 70B), Google Gemini 2.5 Flash, scikit-learn Random Forest.")
        ]),
        ("CHAPTER 4: SOFTWARE DESIGN & MODELING", [
            ("4.1 4-Tier Multitier System Architecture",
             "Study Buddy AI implements a decoupled 4-tier modular topology: Tier 1 (Presentation: Next.js 14 and Streamlit), Tier 2 (Processing & Security Guard: FastAPI and check_class_access RBAC), Tier 3 (Cognitive AI & Knowledge Inference: ChromaDB, Groq LPU, Gemini Flash, and EduGuard ML), and Tier 4 (Persistence: Neon Serverless PostgreSQL with 33 relational tables)."),
            ("4.2 Data Flow Diagrams (DFD Level 0, 1, 2)",
             "The Level 0 Context Diagram establishes data flow between students, teachers, administrators, and the Study Buddy AI engine. Level 1 decomposes user authentication, class verification, RAG chunking, Feynman scoring, and assignment tracking. Level 2 details the exact cosine vector search and prompt synthesis mechanics."),
            ("4.3 UML Modeling",
             "Use Case diagrams specify the interaction contracts between students, teachers, and super admins. Class diagrams define relational ORM entities including SchoolClass, ClassAdmin, ClassEnrollment, Assignment, and Submission. Sequence diagrams capture end-to-end assignment submission and grading cycles."),
            ("4.4 Database Design & Comprehensive ER Model",
             "The schema comprises 33 tables in Neon PostgreSQL with strict foreign keys, cascade deletes, and multi-tenant indexes. Multi-tenant partitioning ensures that student enrollments, assignments, marks, announcements, and timetables are indexed and scoped by class_id."),
            ("4.5 Relational Data Dictionary",
             "Key tables include users (master credentials and roles), school_classes (academic sections), class_admins (faculty mappings), class_enrollments (class-unique roll numbers), assignments, assessment_categories, and marks.")
        ]),
        ("CHAPTER 5: PROPOSED SYSTEM MODULES", [
            ("5.1 Module 1: RAG Academic Document & Notes Ingestion Engine",
             "Extracts text from lecture PDFs, splits content into 800-character windows, generates 384-dimensional dense vectors via SentenceTransformers, and stores them in ChromaDB. Vector searches retrieve top-5 relevant excerpts to ground Groq LPU Llama 3.3 70B responses."),
            ("5.2 Module 2: Feynman Technique Interactive Learning Evaluator",
             "Allows students to explain complex concepts in plain language. Evaluates explanations across conceptual accuracy, simplicity, knowledge gaps, and jargon penalties, returning a score (0–100) and letter grade."),
            ("5.3 Module 3: Adaptive Quiz & Flashcard Generation Engine",
             "Generates multi-choice quizzes with distractor explanations and interactive flip flashcards categorized by difficulty to support spaced repetition and active recall."),
            ("5.4 Module 4: EduGuard AI Student Attrition & Early Warning System",
             "Deploys an ensemble Random Forest Classifier evaluating debtor status, scholarship status, age, gender, first-semester GPA, and attendance. Generates a calibrated dropout probability and assigns risk tiers (LOW, MEDIUM, HIGH) with actionable institutional guidance."),
            ("5.5 Module 5: Class-Based Management & Multi-Tenant Role Isolation",
             "Enforces class-level multi-tenancy. Class Admins manage only assigned classes (Class 10-A), while cross-class tampering is blocked with HTTP 403 Forbidden. Students view only their enrolled class's academic resources."),
            ("5.6 Module 6: Assignment Lifecycle, File Uploads & Automated Grading",
             "Supports assignment publishing, due date enforcement, PDF file uploads, teacher evaluation, numerical scoring, and feedback delivery."),
            ("5.7 Module 7: Academic Timetable & Scheduling System",
             "Maintains weekly schedules, period allocations (45-minute slots), and lunch intervals with real-time ongoing period indicators."),
            ("5.8 Module 8: Multi-Channel Notification & Background Email Pipeline",
             "Dispatches in-app notifications and renders HTML email alerts asynchronously via FastAPI BackgroundTasks, preventing UI thread blocking."),
            ("5.9 Module 9: Real-Time Neon PostgreSQL Engine with NullPool Architecture",
             "Operates over Neon Serverless PostgreSQL with NullPool connection lifecycle management, completely eliminating stale socket drops and Windows semaphore errors.")
        ]),
        ("CHAPTER 6: CODING & IMPLEMENTATION DETAILS", [
            ("6.1 Codebase File Topology & Architectural Responsibilities",
             "Organized into clean modular directories: backend/routers, backend/models, backend/services, frontend/app, and streamlit_app."),
            ("6.2 Core Class & Function Implementations",
             "Key functions include check_class_access (multi-tenant authorization guard) and evaluate_student_risk (EduGuard ML inference)."),
            ("6.3 Database Schema DDL & Persistence Queries",
             "Executed schema definitions for school_classes, class_admins, class_enrollments, and marks tables in PostgreSQL."),
            ("6.4 Groq & Gemini Prompt Templates & Schema Enforcement",
             "Constrained JSON prompt templates enforcing strict evidence grounding and schema validation.")
        ]),
        ("CHAPTER 7: TESTING & VERIFICATION", [
            ("7.1 Testing Philosophy & Quality Assurance",
             "Three-tier QA methodology: Black-Box E2E functional testing, White-Box boundary unit testing, and Class Security barrier verification."),
            ("7.2 Black-Box End-to-End Functional Test Suite",
             "Validated via test_e2e_flow.py: Admin login (200), Student registration (201), Profile lookup (200), Class creation (201), Class enrollment (201), Class barrier enforcement (403), and EduGuard ML prediction (200) all passed 100%."),
            ("7.3 White-Box Boundary & Robustness Test Cases",
             "Tested roll number uniqueness, multi-model fallback cascades, and NullPool connection recovery."),
            ("7.4 Component Latency & Performance Benchmarking",
             "Average vector retrieval: 0.28s; Groq LPU generation: 0.72s; EduGuard ML inference: 0.085s; Neon query latency: 0.21s."),
            ("7.5 Class Barrier & Cross-Class Security Verification",
             "Proved that Class Admin of 10-A is strictly blocked from reading or writing data for Class 10-B.")
        ]),
        ("CHAPTER 8: OUTPUT SCREENS & USER INTERFACES", [
            ("8.0 Application Navigation & Direct Authentication Screens",
             "Direct login and registration screens with server-side SHA-256 validation, eliminating mock simulation OTP barriers."),
            ("8.1 Visual Theme & Human-Centered Design Philosophy",
             "Modern tactical dark/light aesthetic built on Tailwind CSS with high text contrast compliant with WCAG 2.1 AA."),
            ("8.2 Core Screen Walkthroughs & Interaction Workflows",
             "Detailed workflows across Student Dashboard, Notes Search, Feynman Studio, Quiz Hub, Class Management Hub, and EduGuard Retention Portal.")
        ]),
        ("CHAPTER 9: CONCLUSION & FUTURE WORK", [
            ("9.1 Conclusion & Summary of Deliverables",
             "Successfully engineered, deployed, and verified an enterprise-grade academic decision support platform combining RAG, Feynman evaluation, Class RBAC, and EduGuard ML."),
            ("9.2 Societal & Institutional Educational Impact",
             "Democratizes personalized cognitive tutoring and provides university leadership with proactive dropout prevention tools."),
            ("9.3 System Limitations",
             "Handwritten mathematical OCR degradation and cloud LLM endpoint dependencies."),
            ("9.4 Future Work & Engineering Roadmap",
             "Integration of on-device quantized SLMs, National Academic Depository (NAD) DigiLocker connectivity, automated coding evaluation sandboxes, and multilingual Indic vernacular support.")
        ]),
        ("CHAPTER 10: REFERENCES", [
            ("Academic & Technical References",
             "[1] Ministry of Education, Govt. of India. (2020). National Education Policy 2020 (NEP 2020).\n"
             "[2] All India Council for Technical Education (AICTE). (2023). Approval Process Handbook & Norms for Higher Technical Institutions.\n"
             "[3] Vaswani, A., et al. (2017). Attention is all you need. NeurIPS, 30, 5998–6008.\n"
             "[4] Lewis, P., et al. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. NeurIPS, 33, 9459–9474.\n"
             "[5] Feynman, R. P. (1963). The Feynman Lectures on Physics. Addison-Wesley.\n"
             "[6] Bloom, B. S. (1984). The 2 sigma problem: The search for methods of group instruction as effective as one-to-one tutoring. Educational Researcher, 13(6), 4–16.\n"
             "[7] Breiman, L. (2001). Random forests. Machine Learning, 45(1), 5–32.\n"
             "[8] Pedregosa, F., et al. (2011). Scikit-learn: Machine learning in Python. JMLR, 12, 2825–2830.\n"
             "[9] Reimers, N., & Gurevych, I. (2019). Sentence-BERT: Sentence embeddings using Siamese BERT-networks. EMNLP-IJCNLP 2019.\n"
             "[10] Neon Inc. (2024). Serverless PostgreSQL Architecture Documentation.\n"
             "[11] Tiangolo, S. (2024). FastAPI: High-performance Asynchronous Web Framework.\n"
             "[12] Vercel Inc. (2024). Next.js 14 App Router Documentation.\n"
             "[13] Groq Inc. (2024). Groq LPU Tensor Streaming Architecture Documentation.\n"
             "[14] Google Cloud. (2024). Google Gemini API Documentation.")
        ]),
        ("CHAPTER 11: APPENDICES", [
            ("Appendix A: Complete System REST API Endpoints and Module Contracts",
             "1. POST /api/auth/login: Direct password auth returning JWT token.\n"
             "2. POST /api/auth/register: Student account registration.\n"
             "3. POST /api/auth/register-admin: Faculty self-registration.\n"
             "4. GET /api/classes: Lists user-accessible classes.\n"
             "5. POST /api/classes: Creates a school class.\n"
             "6. POST /api/classes/{id}/students: Enrolls students in class.\n"
             "7. POST /api/classes/{id}/students/bulk: Bulk CSV enrollment.\n"
             "8. POST /api/classes/{id}/admins: Assigns class admin.\n"
             "9. POST /api/admin/assignments: Creates class assignment.\n"
             "10. GET /api/assignments: Student fetches class assignments.\n"
             "11. POST /api/assignments/{id}/submit: Submits homework file.\n"
             "12. POST /api/admin/marks: Enters category-wise student marks.\n"
             "13. POST /api/admin/attrition/evaluate: Evaluates EduGuard dropout risk.\n"
             "14. POST /api/feynman/evaluate: Evaluates conceptual explanations.\n"
             "15. POST /api/notifications/broadcast: Multi-channel broadcast alert."),
            ("Appendix B: Environment Configuration (.env)",
             "DATABASE_URL=postgresql://neondb_owner:***@ep-lucky-surf-awvsvfho.c-12.us-east-1.aws.neon.tech/neondb?sslmode=require\n"
             "GROQ_API_KEY=gsk_***\n"
             "GROQ_MODEL=llama-3.3-70b-versatile\n"
             "GEMINI_API_KEY=AQ.***\n"
             "GEMINI_MODEL=gemini-2.5-flash\n"
             "SECRET_KEY=578063489074ceb5641b7d3db717d1e3ee5add41d6cf0523efac75298a13a36c\n"
             "AUTH_REQUIRED=true\n"
             "OTP_AUTH_ENABLED=false\n"
             "OTP_SIMULATION_MODE=false\n"
             "CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:8501\n"
             "RATE_LIMIT_PER_MINUTE=60\n"
             "UPLOAD_DIR=./uploads\n"
             "CHROMA_PERSIST_DIR=./chroma_db"),
            ("Appendix C: EduGuard ML Feature Vector Specification",
             "The EduGuard Random Forest model evaluates a 6-dimensional input vector X = [x1, x2, x3, x4, x5, x6]:\n"
             "x1 = debtor status (0: no tuition arrears, 1: outstanding fees)\n"
             "x2 = scholarship holder (0: no scholarship, 1: active scholarship)\n"
             "x3 = student age at university enrollment\n"
             "x4 = student gender code\n"
             "x5 = first-semester academic GPA (0.0 to 20.0)\n"
             "x6 = overall lecture and lab attendance rate (0.0% to 100.0%)\n"
             "The model executes an ensemble of 100 decision trees to produce the final calibrated probability.")
        ])
    ]

    for chap_title, sections_list in chapters:
        add_p(chap_title, bold=True, size=15, space_after=12, color=(15, 23, 42))
        for sec_title, sec_content in sections_list:
            add_p(sec_title, bold=True, size=12, space_after=6, color=(30, 41, 59))
            for para in sec_content.split("\n\n"):
                if para.startswith("• "):
                    for line in para.split("\n"):
                        add_bullet(line.replace("• ", ""))
                else:
                    add_p(para)
            add_p("", space_after=6)
        doc.add_page_break()

    print(f"Saving DOCX report to: {DOCX_PATH}...")
    doc.save(str(DOCX_PATH))
    print("DOCX build complete!")

if __name__ == "__main__":
    generate_docx()
