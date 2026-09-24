# University of Bamenda Academic Identity & Document Formatting Platform

An automated AI and rule-based document auditing and restructuring engine built specifically for **The University of Bamenda (UBa)** and the **College of Technology (COLTECH)**.

## Features

1. **Split-Second Structural & Institutional Audit**:
   - Ingests `.docx` or `.pdf` manuscripts.
   - Evaluates compliance against UBa Senate Regulations & COLTECH 2020 Guidelines.
   - Computes an Institutional Compliance Score (0–100%).
   - Flags missing preliminaries, heading violations, and margin discrepancies.

2. **Automated One-Click Restructuring**:
   - **Cover & Title Pages**:
     - Official Republic of Cameroon bilingual banner.
     - **Dual Logos** for COLTECH (University of Bamenda Crest on the left, College of Technology Emblem on the right).
     - Central crest for general UBa faculties (FS, FALSH, FES, HTTC, HICM, HITL).
     - Correct metadata placement: Title ($\le 15$ words), Candidate Name (Surname in UPPERCASE), Registration Number, Supervisor name & academic rank, Month & Year.
   - **Statutory Preliminary Pages**:
     - Copyright page.
     - Official Declaration of Originality with candidate matricule and degree.
     - Official Certification of Corrections with sign-off lines for Supervisor, Head of Department (HOD), and Director.
     - Acceptance page (MSc / PhD).
     - Abstract with $\le 6$ Keywords.
     - French Résumé with Title, Abstract translation, and Mots-clés.
     - Dedication & Acknowledgements.
     - Automated Table of Contents with dot leaders.
     - Automated List of Tables, List of Figures, and List of Abbreviations.
   - **Strict Typographic & Layout Enforcement**:
     - Paper Size: White A4 ($21.0 \times 29.7\text{ cm}$), text strictly **Justified**.
     - **Binding Margin**: **$4.0\text{ cm}$** Inside (left), **$2.0\text{ cm}$** Top, Bottom, Outside.
     - **Font**: Times New Roman throughout (`14 pt` bold centered chapter headings on 2 lines, `12 pt` bold subheadings, `12 pt` regular body).
     - **Line Spacing**: $1.5$ for body text; $1.0$ (single) for tables, legends, and APA references.
     - **Dual Pagination**: Lowercase Roman numerals (`i, ii, iii...`) for preliminary pages; Arabic numerals (`1, 2, 3...`) for main chapters starting at Chapter 1.

3. **Clean Live Visual Preview & Instant Downloads**:
   - Page-by-page high-resolution visual browser viewer with zoom, page-flip, thumbnail strip, and visual $4.0\text{ cm}$ binding margin guide.
   - One-click download of editable Word Document (`.docx`) with native Word styles.
   - One-click download of print-ready Document (`.pdf`) compiled via headless LibreOffice.

## Architecture

- **Backend**: FastAPI, `python-docx`, `pypdf`, `Pillow`, `pdftoppm`, LibreOffice headless.
- **Frontend**: Vanilla ES6+, CSS3 design system with UBa institutional gold and deep navy theme, interactive preview canvas, and compliance gauge.
- **Assets**: Extracted high-resolution University of Bamenda crest (`uba_logo.png`), College of Technology emblem (`coltech_logo.png`), and official Director stamp (`coltech_director_stamp.png`).

## Running the Platform

## Running the Platform

### 1. Start the Backend Server (FastAPI + Integrated UI)

Run from the project root:

```bash
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Open your browser at `http://localhost:8000/`. The backend serves the full React UI, all API endpoints, and static assets.

### 2. Run the React Frontend in Development Mode

If you are modifying the React frontend with Vite hot-reload:

```bash
cd frontend-react
npm run dev
```

The Vite dev server runs at `http://localhost:3000/` (proxied to the FastAPI backend at port 8000).

## Vercel Deployment

This project is pre-configured for instant deployment to [Vercel](https://vercel.com):

1. Push this repository to GitHub: `https://github.com/Tamk-Phils/acade.git`
2. In the Vercel Dashboard, click **Add New...** -> **Project** and import `Tamk-Phils/acade`.
3. Vercel automatically detects the Vite configuration via `vercel.json`:
   - **Framework Preset**: Vite
   - **Build Command**: `npm run build --prefix frontend-react`
   - **Output Directory**: `frontend-react/dist`
   - **Install Command**: `npm install --prefix frontend-react`
4. **Environment Variables**:
   - Set `VITE_API_URL` to your deployed backend URL (e.g. `https://acadformat-api.onrender.com`).
   - If deploying the backend on the same domain/proxy, leave `VITE_API_URL` empty to default to `/api`.

## Running Automated Tests

```bash
python3 -m pytest tests/
```

