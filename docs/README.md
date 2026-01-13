# Documentation Index
## PineOS Referral System

Welcome to the comprehensive documentation for the PineOS Referral System. All documentation is organized by category for easy navigation.

---

## 📋 Product Requirements (PRD)

Understanding what we built and why.

- **[PROJECT_SUMMARY.md](./prd/PROJECT_SUMMARY.md)** - Complete project overview with completion checklist
- **[WHAT_I_BUILT.md](./prd/WHAT_I_BUILT.md)** - Quick reference of all features and components

---

## 🏗️ Design Documents

Architecture and design decisions.

- **[DESIGN_NOTES.md](./design/DESIGN_NOTES.md)** - Low-level design, architecture decisions, and tradeoffs

---

## 📡 API Documentation

How to use the APIs with examples.

- **[API_EXAMPLES.md](./api/API_EXAMPLES.md)** - Comprehensive curl examples for all ledger endpoints
- **[AI_BONUS_EXAMPLES.md](./api/AI_BONUS_EXAMPLES.md)** - Natural language to rule conversion examples (Gemini API feature)

**Interactive API Docs:** http://localhost:8000/docs (when running)

---

## 🏛️ Architecture

Project structure and organization.

- **[PROJECT_STRUCTURE.txt](./architecture/PROJECT_STRUCTURE.txt)** - Complete directory tree with file descriptions

---

## 🔧 Technical Documentation

Deep technical details and fixes.

- **[FIXES_APPLIED.md](./technical/FIXES_APPLIED.md)** - Route path and database name fixes applied
- **[UUID_SERIALIZATION_FIX.md](./technical/UUID_SERIALIZATION_FIX.md)** - Complete UUID serialization audit and fix
- **[UUID_FIX_FINAL.md](./technical/UUID_FIX_FINAL.md)** - Final defense-in-depth UUID fix with recursive cleaning

---

## 💻 Development Guides

Guidelines for developers.

- **[GIT_COMMIT_GUIDE.md](./development/GIT_COMMIT_GUIDE.md)** - Step-by-step guide for organizing Git commits

---

## ✅ Quality Assurance

Testing and review documentation.

- **[TESTING.md](../TESTING.md)** - Comprehensive testing guide with examples (in root directory)
- **[PROFESSIONAL_REVIEW_REPORT.md](./qa/PROFESSIONAL_REVIEW_REPORT.md)** - Complete professional code review and testing report

---

## 🚀 Quick Start

**For users:**
1. Start here: [README.md](../README.md) (in root directory)
2. Check [WHAT_I_BUILT.md](./prd/WHAT_I_BUILT.md) for feature overview
3. Try [API_EXAMPLES.md](./api/API_EXAMPLES.md) for hands-on testing

**For developers:**
1. Read [DESIGN_NOTES.md](./design/DESIGN_NOTES.md) for architecture understanding
2. Review [PROJECT_STRUCTURE.txt](./architecture/PROJECT_STRUCTURE.txt) for codebase layout
3. Follow [GIT_COMMIT_GUIDE.md](./development/GIT_COMMIT_GUIDE.md) for contribution workflow
4. Run tests using [TESTING.md](../TESTING.md)

**For reviewers:**
1. Read [PROJECT_SUMMARY.md](./prd/PROJECT_SUMMARY.md) for complete overview
2. Check [PROFESSIONAL_REVIEW_REPORT.md](./qa/PROFESSIONAL_REVIEW_REPORT.md) for quality assessment
3. Review [DESIGN_NOTES.md](./design/DESIGN_NOTES.md) for design decisions

---

## 📁 Documentation Structure

```
docs/
├── README.md                           # This file - Documentation index
├── prd/                                # Product Requirements
│   ├── PROJECT_SUMMARY.md
│   └── WHAT_I_BUILT.md
├── design/                             # Design Documents
│   └── DESIGN_NOTES.md
├── api/                                # API Documentation
│   ├── API_EXAMPLES.md
│   └── AI_BONUS_EXAMPLES.md
├── architecture/                       # Architecture & Structure
│   └── PROJECT_STRUCTURE.txt
├── technical/                          # Technical Documentation
│   ├── FIXES_APPLIED.md
│   ├── UUID_FIX_FINAL.md
│   └── UUID_SERIALIZATION_FIX.md
├── development/                        # Development Guides
│   └── GIT_COMMIT_GUIDE.md
└── qa/                                 # Quality Assurance
    └── PROFESSIONAL_REVIEW_REPORT.md

Note: TESTING.md is in the root directory (../TESTING.md)
```

---

## 🔗 Related Documentation

- **[Main README](../README.md)** - Project README in root directory
- **[Postman Collection](../postman_collection.json)** - Ready-to-use API collection
- **[Docker Compose](../docker-compose.yml)** - Infrastructure configuration
- **[Backend README](../backend/README.md)** - Backend-specific documentation (if exists)

---

## 📞 Support

For questions or issues:
1. Check the relevant documentation section above
2. Review the [PROFESSIONAL_REVIEW_REPORT.md](./qa/PROFESSIONAL_REVIEW_REPORT.md) for known issues
3. Consult the [API Documentation](./api/API_EXAMPLES.md) for usage examples

---

**Last Updated:** 2026-01-13  
**Version:** 1.0.0  
**Status:** Production Ready
